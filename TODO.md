# TODO: Fix Database Schema Mismatch

## Task
Fix the database error that occurs when accessing `/api/admin/modules` endpoint.

## Steps
- [x] 1. Analyze the error and understand the root cause
- [x] 2. Add missing columns to models.py (program, year_of_study, external_link)
- [x] 3. Fix get_admin_modules in admin.py to use correct column names
- [x] 4. Fix upload_module in admin.py to use correct field mappings
- [x] 5. Test the fix

## Issue Details
The error occurs because admin.py queries columns that don't exist in the Module model:
- `program` - doesn't exist (should map to school)
- `year_of_study` - doesn't exist
- `external_link` - doesn't exist
