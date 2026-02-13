from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging

# Modular imports from your production structure
from app.db.supabase import insert_one, select_all, select_one, update_one, delete_one
from app.dependencies import get_current_user, get_current_admin_user
from app.schemas.schemas import ProductCreate, ProductUpdate, ProductResponse

# Setup logging for inventory auditing
logger = logging.getLogger(__name__)

router = APIRouter()

# ============ PRODUCT READ OPERATIONS ============

@router.get("/", response_model=List[ProductResponse])
async def get_products(current_user: dict = Depends(get_current_user)):
    """
    Retrieves all products belonging to the current user's branch.
    Ensures users can never see inventory from other stores.
    """
    try:
        # Fetch products filtered strictly by the user's branch_id for data isolation
        products = await select_all("products", {"branch_id": current_user["branch_id"]})
        return products
    except Exception as e:
        logger.error(f"Failed to fetch products: {str(e)}")
        return []

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product_details(
    product_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch specific product details. 
    Verification: Confirms product_id exists within the user's specific branch_id.
    """
    product = await select_one("products", {
        "product_id": product_id, 
        "branch_id": current_user["branch_id"]
    })
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Product not found in your branch inventory"
        )
    return product

# ============ PRODUCT WRITE OPERATIONS ============

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Creates a new product record. 
    Security: Automatically injects branch_id and creator user_id from the JWT.
    """
    # Standardizing to model_dump() for Pydantic v2 compatibility
    data = product_data.model_dump()
    data.update({
        "branch_id": current_user["branch_id"],
        "created_by": current_user["user_id"]
    })
    
    product = await insert_one("products", data)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to initialize product in database"
        )
    
    logger.info(f"📦 Product '{data.get('name')}' created by user {current_user['user_id']}")
    return product

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Updates an existing product.
    Partial updates are supported (exclude_unset=True).
    """
    # Verify ownership and branch isolation before updating
    existing = await select_one("products", {
        "product_id": product_id, 
        "branch_id": current_user["branch_id"]
    })
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Product not found"
        )

    # Use model_dump(exclude_unset=True) to update only provided fields
    updated = await update_one(
        "products", 
        {"product_id": product_id}, 
        product_data.model_dump(exclude_unset=True)
    )
    return updated

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Removes a product from the inventory.
    Admin Only: Requires administrative privileges to delete stock records.
    """
    # Ensure the product belongs to the admin's branch before deletion
    existing = await select_one("products", {
        "product_id": product_id, 
        "branch_id": current_user["branch_id"]
    })
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Product not found"
        )

    success = await delete_one("products", {"product_id": product_id})
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to remove product"
        )
    
    return None