from supabase import create_client, Client
from app.core.config import settings
import logging

# Setup structured logging for database auditing
logger = logging.getLogger(__name__)

# Initialize a single, shared Supabase client instance (Singleton)
# Uses the Service Role Key to bypass RLS for administrative backend tasks.
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)

# ============ CORE CRUD HELPERS ============

async def insert_one(table: str, data: dict):
    """
    Inserts a single record into the specified table.
    Returns the inserted record or None if the operation fails.
    """
    try:
        if not data:
            return None
        result = supabase.table(table).insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"❌ DB Insert Error [{table}]: {str(e)}")
        return None

async def select_one(table: str, filters: dict):
    """
    Retrieves the first record matching the provided filters.
    """
    try:
        query = supabase.table(table).select("*")
        for key, value in filters.items():
            query = query.eq(key, value)
        
        result = query.limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"❌ DB Select Error [{table}]: {str(e)}")
        return None

async def select_all(table: str, filters: dict = None):
    """
    Retrieves all records matching the filters.
    Returns an empty list if no records are found or an error occurs.
    """
    try:
        query = supabase.table(table).select("*")
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        
        result = query.execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"❌ DB Select All Error [{table}]: {str(e)}")
        return []

async def update_one(table: str, filters: dict, data: dict):
    """
    Updates records matching the filters with the provided data.
    """
    try:
        if not data or not filters:
            return None
            
        query = supabase.table(table).update(data)
        for key, value in filters.items():
            query = query.eq(key, value)
            
        result = query.execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"❌ DB Update Error [{table}]: {str(e)}")
        return None

async def delete_one(table: str, filters: dict) -> bool:
    """
    Deletes records matching the filters.
    Returns True if at least one record was deleted, False otherwise.
    """
    try:
        if not filters:
            return False
            
        query = supabase.table(table).delete()
        for key, value in filters.items():
            query = query.eq(key, value)
            
        result = query.execute()
        return len(result.data) > 0 if result.data else False
    except Exception as e:
        logger.error(f"❌ DB Delete Error [{table}]: {str(e)}")
        return False

# ============ SPECIFIC BUSINESS OPERATIONS ============

async def create_user_with_branch(user_data: dict, branch_data: dict):
    """
    Atomic-like operation to create a branch and its first admin user.
    """
    try:
        # 1. Create the branch first
        branch = await insert_one("branches", branch_data)
        if not branch:
            logger.error("Failed to create branch during first-signup.")
            return None
            
        # 2. Prepare user data with the new branch ID
        # Ensuring branch_id is treated as a string or int based on DB requirements
        user_data.update({
            "branch_id": branch["branch_id"],
            "is_admin": True,      # First user is always admin
            "is_verified": False,  # Verification required via OTP
            "is_active": True
        })
        
        # 3. Create the user
        user = await insert_one("users", user_data)
        if not user:
            logger.error(f"Failed to create admin user for branch {branch['branch_id']}.")
            # Note: In a true production environment, you might consider deleting the orphaned branch here.
            return None
            
        return user
    except Exception as e:
        logger.error(f"❌ Critical Signup Transaction Error: {str(e)}")
        return None

async def get_users_by_branch(branch_id: str):
    """
    Helper to fetch all users belonging to a specific store.
    """
    # Cast branch_id to string to ensure compatibility with TokenData schema expectations
    return await select_all("users", {"branch_id": str(branch_id)})