from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging

# Modular imports from your production structure
from app.db.supabase import (
    insert_one, select_all, select_one, update_one, delete_one, select_many
)
from app.dependencies import get_current_user, get_current_admin_user
from app.schemas.schemas import (
    ProductCreate, ProductUpdate, ProductResponse, ProductDetailResponse,
    BankOffer, EMIOffer, UPIOffer
)

# Setup logging for inventory and offer auditing
logger = logging.getLogger(__name__)

router = APIRouter()

# ============ PRODUCT READ OPERATIONS ============

@router.get("/", response_model=List[ProductResponse])
async def get_products(current_user: dict = Depends(get_current_user)):
    """
    Retrieves all products for the branch.
    Accessible by: Staff and Admin.
    """
    try:
        products = await select_all("products", {"branch_id": current_user["branch_id"]})
        return products
    except Exception as e:
        logger.error(f"Failed to fetch products: {str(e)}")
        return []

@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product_details(
    product_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """
    Aggregated fetch: Returns product + all related Bank, EMI, and UPI offers.
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

    # Parallel fetch for related offers from sub-tables
    product["bank_offers"] = await select_many("bank_offers", {"product_id": product_id})
    product["emi_offers"] = await select_many("emi_offers", {"product_id": product_id})
    product["upi_offers"] = await select_many("upi_offers", {"product_id": product_id})

    return product

# ============ PRODUCT WRITE OPERATIONS ============

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: dict = Depends(get_current_user) # Permission: Staff & Admin
):
    """
    Creates a new laptop entry.
    Fixes the 'invalid input syntax for type integer' by rounding price.
    """
    data = product_data.model_dump()
    
    # SECURITY & DATA FIX: Round price to nearest integer to satisfy DB INT type
    if "price" in data and data["price"] is not None:
        data["price"] = int(round(data["price"]))

    data.update({
        "branch_id": current_user["branch_id"],
        "created_by": current_user["user_id"]
    })
    
    product = await insert_one("products", data)
    if not product:
        # If DB returns 400, it reaches here as None
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Failed to save product. Ensure price and stock are whole numbers."
        )
    
    logger.info(f"📦 Product '{data.get('name')}' added by {current_user['name']} (ID: {current_user['user_id']})")
    return product

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    current_user: dict = Depends(get_current_user) # Permission: Staff & Admin
):
    """Updates product info. Both Staff and Admins can edit details."""
    existing = await select_one("products", {
        "product_id": product_id, 
        "branch_id": current_user["branch_id"]
    })
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    update_dict = product_data.model_dump(exclude_unset=True)
    
    # DATA FIX: Round price if it's being updated
    if "price" in update_dict and update_dict["price"] is not None:
        update_dict["price"] = int(round(update_dict["price"]))

    updated = await update_one(
        "products", 
        {"product_id": product_id}, 
        update_dict
    )
    return updated

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: dict = Depends(get_current_admin_user) # Permission: Admin Only
):
    """
    Admin Only: Removes product. 
    Maintains higher security for deletion.
    """
    existing = await select_one("products", {
        "product_id": product_id, 
        "branch_id": current_user["branch_id"]
    })
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    await delete_one("products", {"product_id": product_id})
    return None

# ============ OFFER MANAGEMENT OPERATIONS ============

@router.post("/{product_id}/bank-offers", status_code=status.HTTP_201_CREATED)
async def add_bank_offer(
    product_id: str,
    offer: BankOffer,
    current_user: dict = Depends(get_current_user)
):
    """Adds a Bank discount. Staff and Admins can manage offers."""
    data = offer.model_dump()
    data["product_id"] = product_id
    
    result = await insert_one("bank_offers", data)
    return {"success": True, "data": result}

@router.post("/{product_id}/emi-offers", status_code=status.HTTP_201_CREATED)
async def add_emi_offer(
    product_id: str,
    offer: EMIOffer,
    current_user: dict = Depends(get_current_user)
):
    """Adds an EMI plan. Staff and Admins can manage offers."""
    data = offer.model_dump()
    data["product_id"] = product_id
    
    result = await insert_one("emi_offers", data)
    return {"success": True, "data": result}

@router.post("/{product_id}/upi-offers", status_code=status.HTTP_201_CREATED)
async def add_upi_offer(
    product_id: str,
    offer: UPIOffer,
    current_user: dict = Depends(get_current_user)
):
    """Adds a UPI discount. Staff and Admins can manage offers."""
    data = offer.model_dump()
    data["product_id"] = product_id
    
    result = await insert_one("upi_offers", data)
    return {"success": True, "data": result}