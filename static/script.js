/**
 * UR Hub - Social Learning Stream
 * Interactive functionality for posts, comments, likes, shares, and expansions
 */

let currentUser = JSON.parse(localStorage.getItem('ur_user') || 'null');
let authToken = localStorage.getItem('ur_access_token');

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    initializePosts();
    autoResizeTextareas();
    loadPosts();
});

/**
 * Load posts from localStorage
 */
function loadPosts() {
    // Clear old cached posts to start fresh
    localStorage.removeItem('ur_hub_posts');
    
    const postStream = document.getElementById('postStream');
    // Empty stream - no sample posts
    
    initializePosts();
}

/**
 * Initialize posts
 */
function initializePosts() {
    // Posts will be added dynamically
}

/**
 * Create a post element from data
 */
function createPostElement(post) {
    const article = document.createElement('article');
    article.className = 'post';
    article.dataset.expanded = 'false';
    article.dataset.id = post.id;
    
    const timeAgo = formatTimeAgo(post.timestamp);
    const minutesAgo = (Date.now() - post.timestamp) / (1000 * 60);
    const canDelete = post.isOwn && minutesAgo <= 10;
    
    const avatarColors = ['#1e40af', '#1e3a8a', '#1e3a2f', '#0f172a', '#1e2939'];
    const avatarColor = avatarColors[post.id % avatarColors.length];
    
    const avatarSvg = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Ccircle cx='20' cy='20' r='20' fill='${encodeURIComponent(avatarColor)}'/%3E%3Ctext x='20' y='25' text-anchor='middle' fill='white' font-size='12' font-weight='bold'%3E${post.initials}%3C/text%3E%3C/svg%3E`;
    
    // Render comments
    const commentsHtml = post.comments && post.comments.length > 0 
        ? post.comments.map(c => `
            <div class="comment-item">
                <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='16' fill='%233b82f6'/%3E%3Ctext x='16' y='20' text-anchor='middle' fill='white' font-size='10' font-weight='bold'%3E${c.initials}%3C/text%3E%3C/svg%3E" alt="${c.author}" class="comment-avatar">
                <div class="comment-content">
                    <div class="comment-header">
                        <span class="comment-author">${c.author}</span>
                        <span class="comment-time">${formatTimeAgo(c.timestamp)}</span>
                    </div>
                    <p class="comment-text">${escapeHtml(c.content)}</p>
                </div>
            </div>
        `).join('')
        : '';
    
    article.innerHTML = `
        <div class="identity-row">
            <img src="${avatarSvg}" alt="${post.author}" class="avatar">
            <div class="identity-text">
                <span class="name">${post.author}</span>
                <span class="faculty">${post.faculty}</span>
                <span class="dot">·</span>
                <span class="time">${timeAgo}</span>
            </div>
            ${canDelete ? `
                <button class="delete-btn" onclick="deletePost(${post.id}, this)">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            ` : ''}
        </div>
        
        <div class="content">
            <p>${escapeHtml(post.content)}</p>
        </div>
        
        <div class="action-row">
            <button class="action-btn comment-btn" onclick="toggleComments(${post.id}, this)">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span>${post.commentsCount || 0}</span>
            </button>
            <button class="action-btn share-btn" onclick="sharePost(${post.id}, this)">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path>
                    <polyline points="16 6 12 2 8 6"></polyline>
                    <line x1="12" y1="2" x2="12" y2="15"></line>
                </svg>
            </button>
            <button class="action-btn appreciate-btn ${post.appreciated ? 'appreciated' : ''}" onclick="appreciatePost(${post.id}, this)">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="${post.appreciated ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
                </svg>
                <span>${post.appreciates || 0}</span>
            </button>
            <button class="action-btn expand-btn" onclick="toggleExpand(this)">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="19 12 12 19 5 12"></polyline>
                    <line x1="12" y1="5" x2="12" y2="19"></line>
                </svg>
            </button>
        </div>
        
        <div class="comments-section" id="comments-${post.id}" style="display: none;">
            <div class="comments-list" id="comments-list-${post.id}">
                ${commentsHtml}
            </div>
            <div class="comment-input-wrapper">
                <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Ccircle cx='20' cy='20' r='20' fill='%231e40af'/%3E%3Ctext x='20' y='25' text-anchor='middle' fill='white' font-size='14' font-weight='bold'%3EYU%3C/text%3E%3C/svg%3E" alt="You" class="comment-avatar">
                <input type="text" class="comment-input" id="comment-input-${post.id}" placeholder="Write a comment..." onkeypress="handleCommentKeypress(event, ${post.id})">
                <button class="comment-submit" onclick="addComment(${post.id})">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                </button>
            </div>
        </div>
    `;
    
    return article;
}

/**
 * Format timestamp to relative time
 */
function formatTimeAgo(timestamp) {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d`;
    
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Auto-resize textareas
 */
function autoResizeTextareas() {
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    });
}

/**
 * Toggle post expansion
 */
function toggleExpand(button) {
    const post = button.closest('.post');
    const isExpanded = post.dataset.expanded === 'true';
    const content = post.querySelector('.content');
    
    if (isExpanded) {
        post.dataset.expanded = 'false';
        button.style.transform = 'rotate(0deg)';
        content.style.maxHeight = '120px';
    } else {
        post.dataset.expanded = 'true';
        button.style.transform = 'rotate(180deg)';
        content.style.maxHeight = 'none';
    }
}

/**
 * Create a new post
 */
function createPost() {
    const postInput = document.getElementById('postInput');
    const content = postInput.value.trim();
    
    if (!content) {
        showToast('Please write something to post');
        return;
    }
    
    const newPost = {
        id: Date.now(),
        author: 'Your Name',
        initials: 'YU',
        faculty: 'School of Engineering',
        timestamp: Date.now(),
        content: content,
        comments: [],
        commentsCount: 0,
        appreciates: 0,
        appreciated: false,
        isOwn: true
    };
    
    const postStream = document.getElementById('postStream');
    const postElement = createPostElement(newPost);
    postStream.insertBefore(postElement, postStream.firstChild);
    
    // Save to localStorage
    savePosts();
    
    postInput.value = '';
    postInput.style.height = 'auto';
    
    showToast('Posted successfully!');
}

/**
 * Save posts to localStorage
 */
function savePosts() {
    const postStream = document.getElementById('postStream');
    const posts = [];
    
    postStream.querySelectorAll('.post').forEach(postEl => {
        posts.push({
            id: parseInt(postEl.dataset.id),
            content: postEl.querySelector('.content p').textContent,
            timestamp: Date.now() - parseInt(postEl.querySelector('.time').textContent.replace(/[^0-9]/g, '') || 0) * 60000
        });
    });
    
    localStorage.setItem('ur_hub_posts', JSON.stringify(posts));
}

/**
 * Delete a post
 */
function deletePost(postId, button) {
    event.stopPropagation();
    
    const post = button.closest('.post');
    const minutesAgo = (Date.now() - parseInt(post.dataset.id)) / (1000 * 60);
    
    if (minutesAgo > 10) {
        showToast('You can only delete posts within 10 minutes of posting');
        return;
    }
    
    if (confirm('Are you sure you want to delete this post?')) {
        post.style.opacity = '0';
        post.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            post.remove();
            showToast('Post deleted');
        }, 300);
    }
}

/**
 * Appreciate/Like a post
 */
function appreciatePost(postId, button) {
    const span = button.querySelector('span');
    const count = parseInt(span.textContent);
    const isAppreciated = button.classList.toggle('appreciated');
    
    span.textContent = isAppreciated ? count + 1 : count - 1;
    
    const svg = button.querySelector('svg');
    svg.setAttribute('fill', isAppreciated ? 'currentColor' : 'none');
    
    showToast(isAppreciated ? 'Appreciated!' : 'Appreciation removed');
}

/**
 * Share a post
 */
function sharePost(postId, button) {
    const post = document.querySelector(`.post[data-id="${postId}"]`);
    const content = post.querySelector('.content').textContent.trim();
    const author = post.querySelector('.name').textContent;
    
    const shareText = `${author}: ${content}`;
    const shareUrl = window.location.href.split('?')[0] + '?post=' + postId;
    
    // Check if Web Share API is available
    if (navigator.share) {
        navigator.share({
            title: 'UR Hub Post',
            text: shareText,
            url: shareUrl
        }).catch(err => {
            console.log('Share cancelled:', err);
            copyToClipboard(shareUrl);
        });
    } else {
        // Fallback: Copy to clipboard
        copyToClipboard(shareUrl);
    }
}

/**
 * Copy to clipboard helper
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Link copied to clipboard!');
    }).catch(() => {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('Link copied to clipboard!');
    });
}

/**
 * Toggle comments section
 */
function toggleComments(postId, button) {
    const commentsSection = document.getElementById(`comments-${postId}`);
    const isHidden = commentsSection.style.display === 'none' || commentsSection.style.display === '';
    
    commentsSection.style.display = isHidden ? 'block' : 'none';
    
    if (isHidden) {
        const input = document.getElementById(`comment-input-${postId}`);
        input.focus();
    }
}

/**
 * Handle comment input keypress
 */
function handleCommentKeypress(event, postId) {
    if (event.key === 'Enter') {
        addComment(postId);
    }
}

/**
 * Add a comment
 */
function addComment(postId) {
    const input = document.getElementById(`comment-input-${postId}`);
    const content = input.value.trim();
    
    if (!content) return;
    
    const commentsList = document.getElementById(`comments-list-${postId}`);
    const commentCountBtn = document.querySelector(`.post[data-id="${postId}"] .comment-btn span`);
    
    const newComment = {
        author: 'Your Name',
        initials: 'YU',
        content: content,
        timestamp: Date.now()
    };
    
    const commentHtml = `
        <div class="comment-item">
            <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='16' fill='%233b82f6'/%3E%3Ctext x='16' y='20' text-anchor='middle' fill='white' font-size='10' font-weight='bold'%3EYU%3C/text%3E%3C/svg%3E" alt="${newComment.author}" class="comment-avatar">
            <div class="comment-content">
                <div class="comment-header">
                    <span class="comment-author">${newComment.author}</span>
                    <span class="comment-time">Just now</span>
                </div>
                <p class="comment-text">${escapeHtml(newComment.content)}</p>
            </div>
        </div>
    `;
    
    commentsList.insertAdjacentHTML('beforeend', commentHtml);
    
    const currentCount = parseInt(commentCountBtn.textContent);
    commentCountBtn.textContent = currentCount + 1;
    
    input.value = '';
    
    showToast('Comment added');
}

/**
 * Show toast notification
 */
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Toggle follow action
 */
function toggleFollow(handle, button) {
    const isFollowing = button.classList.toggle('following');
    button.textContent = isFollowing ? 'Following' : 'Follow';
    button.classList.toggle('btn-primary', !isFollowing);
    button.classList.toggle('btn-secondary', isFollowing);
    
    showToast(isFollowing ? `Following ${handle}` : `Unfollowed ${handle}`);
}

/**
 * Toggle action visibility on focus
 */
function toggleAction(show) {
    const actions = document.querySelectorAll('.post:not(:focus-within) .action-row .action-btn:not(.comment-btn)');
    actions.forEach(action => {
        action.style.opacity = show ? '1' : '0.5';
        action.style.transform = show ? 'scale(1)' : 'scale(0.95)';
    });
}

// Auto-resize function for textarea
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

// Export functions to window for inline onclick handlers
window.toggleExpand = toggleExpand;
window.toggleAction = toggleAction;
window.toggleFollow = toggleFollow;
window.toggleComments = toggleComments;
window.handleCommentKeypress = handleCommentKeypress;
window.addComment = addComment;
window.sharePost = sharePost;
window.deletePost = deletePost;
window.createPost = createPost;
window.appreciatePost = appreciatePost;
window.autoResize = autoResize;
