/*
UR Hub - Profile Page JavaScript
Handles profile display, editing, and user interactions
*/

// Current user data (simulated)
let currentUser = {
    id: 1,
    name: 'YvesUwera',
    fullName: 'Yves Uwera',
    bio: 'Computer Science student | AI enthusiast | Building things that matter',
    faculty: 'School of Engineering',
    program: 'Computer Science',
    year: 'Year 3',
    studentId: '2300001234',
    joinDate: 'September 2024',
    followers: 156,
    following: 89,
    posts: 42,
    interests: ['Machine Learning', 'Data Science', 'Web Development', 'Python'],
    avatar: 'YU',
    isFollowing: false
};

// User being viewed
let viewingUser = null;

// Initialize profile page
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('id');
    
    if (userId) {
        loadUserProfile(parseInt(userId));
    } else {
        loadCurrentUserProfile();
    }
});

// Load current user's profile
function loadCurrentUserProfile() {
    viewingUser = currentUser;
    renderProfile();
    loadUserPosts(currentUser.id);
    updateStats();
}

// Load another user's profile
function loadUserProfile(userId) {
    // Simulate fetching user data
    if (userId === currentUser.id) {
        viewingUser = currentUser;
    } else {
        viewingUser = {
            id: userId,
            name: 'johndoe',
            fullName: 'John Doe',
            bio: 'Mechanical Engineering student | Robotics | 3D Printing enthusiast',
            faculty: 'School of Engineering',
            program: 'Mechanical Engineering',
            year: 'Year 2',
            studentId: '2300005678',
            joinDate: 'September 2024',
            followers: 45,
            following: 67,
            posts: 23,
            interests: ['Robotics', 'CAD', '3D Printing', 'Automation'],
            avatar: 'JD',
            isFollowing: false
        };
    }
    renderProfile();
    loadUserPosts(userId);
    updateStats();
}

// Render profile information
function renderProfile() {
    if (!viewingUser) return;
    
    // Update profile info
    document.getElementById('profile-name').textContent = viewingUser.fullName;
    document.getElementById('profile-handle').textContent = `@${viewingUser.name}`;
    document.getElementById('profile-bio').textContent = viewingUser.bio;
    document.getElementById('join-date').innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="16" y1="2" x2="16" y2="6"></line>
            <line x1="8" y1="2" x2="8" y2="6"></line>
            <line x1="3" y1="10" x2="21" y2="10"></line>
        </svg>
        Joined ${viewingUser.joinDate}
    `;
    
    // Update avatar
    const avatarSvg = getAvatarSVG(viewingUser.avatar || viewingUser.name.substring(0, 2).toUpperCase());
    document.getElementById('profile-avatar').src = avatarSvg;
    
    // Update header title
    document.getElementById('header-title').textContent = viewingUser.fullName;
    
    // Show/hide edit button
    const isOwnProfile = viewingUser.id === currentUser.id;
    document.getElementById('edit-profile-btn').style.display = isOwnProfile ? 'block' : 'none';
    document.getElementById('follow-profile-btn').style.display = isOwnProfile ? 'none' : 'block';
    
    // Update About section
    document.getElementById('about-faculty').textContent = viewingUser.faculty || '-';
    document.getElementById('about-program').textContent = viewingUser.program || '-';
    document.getElementById('about-year').textContent = viewingUser.year || '-';
    document.getElementById('about-student-id').textContent = viewingUser.studentId || '-';
    
    // Update interests
    renderInterests();
}

// Render interests
function renderInterests() {
    const container = document.getElementById('interests-container');
    if (!container) return;
    
    const interests = viewingUser.interests || [];
    if (interests.length === 0) {
        container.innerHTML = '<span class="skill-tag">Add interests...</span>';
    } else {
        container.innerHTML = interests.map(interest => 
            `<span class="skill-tag">${interest}</span>`
        ).join('');
    }
}

// Update stats
function updateStats() {
    if (!viewingUser) return;
    
    document.getElementById('stat-followers').textContent = formatNumber(viewingUser.followers);
    document.getElementById('stat-following').textContent = formatNumber(viewingUser.following);
    document.getElementById('stat-posts').textContent = formatNumber(viewingUser.posts);
    
    // Update follow button state
    const followBtn = document.getElementById('follow-profile-btn');
    if (followBtn) {
        followBtn.textContent = viewingUser.isFollowing ? 'Following' : 'Follow';
        followBtn.classList.toggle('btn-primary', !viewingUser.isFollowing);
        followBtn.classList.toggle('btn-secondary', viewingUser.isFollowing);
    }
}

// Load user's posts
function loadUserPosts(userId) {
    const postsPanel = document.getElementById('posts-panel');
    if (!postsPanel) return;
    
    // Clear old cached posts
    localStorage.removeItem('ur_hub_posts');
    
    // Empty stream
    postsPanel.innerHTML = `
        <div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <h3>No posts yet</h3>
            <p>When you post, your posts will appear here.</p>
        </div>
    `;
    viewingUser.posts = 0;
}

// Format numbers
function formatNumber(num) {
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Format text
function formatText(text) {
    // Handle hashtags
    text = text.replace(/#(\w+)/g, '<span class="hashtag">#$1</span>');
    return text;
}

// Toggle tab
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    
    // Update tab panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `${tabName}-panel`);
    });
}

// Open settings
function openSettings() {
    document.getElementById('settings-panel').classList.add('open');
    document.getElementById('overlay').classList.add('show');
    document.body.style.overflow = 'hidden';
}

// Close settings
function closeSettings() {
    document.getElementById('settings-panel').classList.remove('open');
    document.getElementById('overlay').classList.remove('show');
    document.body.style.overflow = '';
}

// Open edit profile modal
function openEditProfile() {
    const modal = document.getElementById('edit-profile-modal');
    
    // Pre-fill form with current data
    document.getElementById('edit-name').value = viewingUser.fullName;
    document.getElementById('edit-handle').value = viewingUser.name;
    document.getElementById('edit-bio').value = viewingUser.bio || '';
    document.getElementById('edit-faculty').value = viewingUser.faculty || '';
    document.getElementById('edit-program').value = viewingUser.program || '';
    document.getElementById('edit-year').value = viewingUser.year || '';
    document.getElementById('edit-interests').value = (viewingUser.interests || []).join(', ');
    
    modal.classList.add('show');
}

// Close edit profile modal
function closeEditProfile() {
    document.getElementById('edit-profile-modal').classList.remove('show');
}

// Save profile
function saveProfile() {
    viewingUser.fullName = document.getElementById('edit-name').value;
    viewingUser.name = document.getElementById('edit-handle').value;
    viewingUser.bio = document.getElementById('edit-bio').value;
    viewingUser.faculty = document.getElementById('edit-faculty').value;
    viewingUser.program = document.getElementById('edit-program').value;
    viewingUser.year = document.getElementById('edit-year').value;
    viewingUser.interests = document.getElementById('edit-interests').value.split(',').map(s => s.trim()).filter(s => s);
    
    renderProfile();
    closeEditProfile();
    
    // Show success message
    showToast('Profile updated successfully!');
}

// Change avatar
function changeAvatar() {
    document.getElementById('avatar-modal').classList.add('show');
}

// Close avatar modal
function closeAvatarModal() {
    document.getElementById('avatar-modal').classList.remove('show');
}

// Select avatar
function selectAvatar(initials) {
    viewingUser.avatar = initials;
    const avatarSvg = getAvatarSVG(initials);
    document.getElementById('profile-avatar').src = avatarSvg;
    closeAvatarModal();
    showToast('Avatar updated!');
}

// Upload avatar
function uploadAvatar(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            viewingUser.avatar = e.target.result;
            document.getElementById('profile-avatar').src = e.target.result;
            closeAvatarModal();
            showToast('Avatar uploaded!');
        };
        reader.readAsDataURL(input.files[0]);
    }
}

// Toggle follow profile
function toggleFollowProfile() {
    viewingUser.isFollowing = !viewingUser.isFollowing;
    viewingUser.followers += viewingUser.isFollowing ? 1 : -1;
    updateStats();
    
    const btn = document.getElementById('follow-profile-btn');
    btn.textContent = viewingUser.isFollowing ? 'Following' : 'Follow';
    btn.classList.toggle('btn-primary', !viewingUser.isFollowing);
    btn.classList.toggle('btn-secondary', viewingUser.isFollowing);
    
    showToast(viewingUser.isFollowing ? 'Following ' + viewingUser.fullName : 'Unfollowed ' + viewingUser.fullName);
}

// Show followers
function showFollowers() {
    showToast('Followers list coming soon!');
}

// Show following
function showFollowing() {
    showToast('Following list coming soon!');
}

// Show posts
function showPosts() {
    switchTab('posts');
}

// Open notifications
function openNotifications() {
    showToast('Notifications coming soon!');
}

// Open messages
function openMessages() {
    showToast('Direct Messages coming soon!');
}

// Open groups
function openGroups() {
    showToast('Study Groups coming soon!');
}

// Open comment
function openComment(postId) {
    showToast('Comments feature coming soon!');
}

// Share post
function sharePost(postId) {
    const postUrl = window.location.origin + window.location.pathname + '?post=' + postId;
    
    if (navigator.share) {
        navigator.share({
            title: 'UR Hub Post',
            text: 'Check out this post on UR Hub!',
            url: postUrl
        }).catch(err => {
            console.log('Share cancelled:', err);
            copyToClipboard(postUrl);
        });
    } else {
        copyToClipboard(postUrl);
    }
}

// Copy to clipboard helper
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

// View deep read
function viewDeepRead(postId) {
    window.location.href = `post.html?id=${postId}`;
}

// Toggle like
function toggleLike(postId) {
    const btn = document.querySelector(`.post[data-post-id="${postId}"] .like-btn`);
    if (btn) {
        const isLiked = btn.classList.toggle('active');
        const span = btn.querySelector('span');
        const count = parseInt(span.textContent);
        span.textContent = isLiked ? count + 1 : count - 1;
        
        // Update SVG fill
        const svg = btn.querySelector('svg');
        svg.setAttribute('fill', isLiked ? 'currentColor' : 'none');
        
        showToast(isLiked ? 'Appreciated!' : 'Appreciation removed');
    }
}

// Toggle expand post
function toggleExpand(btn) {
    const post = btn.closest('.post');
    const textWrapper = post.querySelector('.post-text');
    const isExpanded = post.classList.toggle('expanded');
    
    if (isExpanded) {
        const fullContent = decodeURIComponent(textWrapper.dataset.fullContent);
        textWrapper.innerHTML = `<p>${fullContent}</p>`;
        btn.style.transform = 'rotate(180deg)';
    } else {
        const fullContent = decodeURIComponent(textWrapper.dataset.fullContent);
        textWrapper.innerHTML = `<p class="text-shortened">${formatText(fullContent)}</p>`;
        btn.style.transform = 'rotate(0deg)';
    }
}

// Show post options
function showPostOptions(postId) {
    showToast('Post options coming soon!');
}

// Confirm logout
function confirmLogout() {
    if (confirm('Are you sure you want to log out?')) {
        window.location.href = 'public.html';
    }
}

// Search functionality
function handleSearch(query) {
    if (query.length > 2) {
        // Filter posts or search users
        console.log('Searching for:', query);
    }
}

// Toast notification
function showToast(message) {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: #1e293b;
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 14px;
        z-index: 2000;
        animation: fadeInUp 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add animation keyframes
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translate(-50%, 20px);
        }
        to {
            opacity: 1;
            transform: translate(-50%, 0);
        }
    }
    @keyframes fadeOut {
        from {
            opacity: 1;
            transform: translate(-50%, 0);
        }
        to {
            opacity: 0;
            transform: translate(-50%, -10px);
        }
    }
`;
document.head.appendChild(style);

// Get avatar SVG
function getAvatarSVG(initials) {
    return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 80'%3E%3Ccircle cx='40' cy='40' r='40' fill='%231e40af'/%3E%3Ctext x='40' y='48' text-anchor='middle' fill='white' font-size='24' font-weight='bold'%3E${initials}%3C/text%3E%3C/svg%3E`;
}
