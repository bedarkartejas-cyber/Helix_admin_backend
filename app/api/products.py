# # from fastapi import APIRouter, Depends, HTTPException, status
# # from typing import List
# # import logging

# # # Modular imports from your production structure
# # from app.db.supabase import (
# #     insert_one, select_all, select_one, update_one, delete_one, select_many
# # )
# # from app.dependencies import get_current_user, get_current_admin_user
# # from app.schemas.schemas import (
# #     ProductCreate, ProductUpdate, ProductResponse, ProductDetailResponse,
# #     CardOfferBase, EMIPlan, UPIOffer
# # )

# # # Setup logging for inventory and financial offer auditing
# # logger = logging.getLogger(__name__)

# # router = APIRouter()

# # # ============ PRODUCT READ OPERATIONS ============

# # @router.get("/", response_model=List[ProductResponse])
# # async def get_products(current_user: dict = Depends(get_current_user)):
# #     """
# #     Retrieves basic list of laptops for the branch.
# #     Accessible by: Staff and Admin.
# #     """
# #     try:
# #         products = await select_all("products", {"branch_id": current_user["branch_id"]})
# #         return products
# #     except Exception as e:
# #         logger.error(f"Failed to fetch products: {str(e)}")
# #         return []

# # @router.get("/{product_id}", response_model=ProductDetailResponse)
# # async def get_product_details(
# #     product_id: str, 
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     """
# #     Aggregated fetch: Returns product + detailed CC, DC, EMI, and UPI data.
# #     This provides the high-detail data for the Sales Assistant UI.
# #     """
# #     # 1. Fetch main product record
# #     product = await select_one("products", {
# #         "product_id": product_id, 
# #         "branch_id": current_user["branch_id"]
# #     })
    
# #     if not product:
# #         raise HTTPException(
# #             status_code=status.HTTP_404_NOT_FOUND, 
# #             detail="Product not found in your branch inventory"
# #         )

# #     # 2. Parallel fetch for new specialized financial tables
# #     product["credit_card_offers"] = await select_many("credit_card_offers", {"product_id": product_id})
# #     product["debit_card_offers"] = await select_many("debit_card_offers", {"product_id": product_id})
# #     product["emi_plans"] = await select_many("emi_plans", {"product_id": product_id})
# #     product["upi_offers"] = await select_many("upi_offers", {"product_id": product_id})

# #     return product

# # # ============ PRODUCT WRITE OPERATIONS ============

# # @router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
# # async def create_product(
# #     product_data: ProductCreate,
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     """
# #     Initial Laptop Creation. Rounds price to satisfy DB Integer type.
# #     """
# #     data = product_data.model_dump()
    
# #     if "price" in data and data["price"] is not None:
# #         data["price"] = int(round(data["price"]))

# #     data.update({
# #         "branch_id": current_user["branch_id"],
# #         "created_by": current_user["user_id"]
# #     })
    
# #     product = await insert_one("products", data)
# #     if not product:
# #         raise HTTPException(
# #             status_code=status.HTTP_400_BAD_REQUEST, 
# #             detail="Failed to initialize product. Check numeric constraints."
# #         )
    
# #     return product

# # @router.put("/{product_id}", response_model=ProductResponse)
# # async def update_product(
# #     product_id: str,
# #     product_data: ProductUpdate,
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     """Updates core laptop info. Accessible by Staff and Admins."""
# #     existing = await select_one("products", {
# #         "product_id": product_id, 
# #         "branch_id": current_user["branch_id"]
# #     })
# #     if not existing:
# #         raise HTTPException(status_code=404, detail="Product not found")

# #     update_dict = product_data.model_dump(exclude_unset=True)
# #     if "price" in update_dict and update_dict["price"] is not None:
# #         update_dict["price"] = int(round(update_dict["price"]))

# #     updated = await update_one("products", {"product_id": product_id}, update_dict)
# #     return updated

# # @router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
# # async def delete_product(
# #     product_id: str,
# #     current_user: dict = Depends(get_current_admin_user)
# # ):
# #     """Admin Only: Deletes laptop and all linked financial offers."""
# #     existing = await select_one("products", {
# #         "product_id": product_id, 
# #         "branch_id": current_user["branch_id"]
# #     })
# #     if not existing:
# #         raise HTTPException(status_code=404, detail="Product not found")

# #     await delete_one("products", {"product_id": product_id})
# #     return None

# # # ============ DETAILED FINANCIAL OFFER OPERATIONS ============

# # @router.post("/{product_id}/credit-card-offers", status_code=status.HTTP_201_CREATED)
# # async def add_credit_card_offer(
# #     product_id: str,
# #     offer: CardOfferBase,
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     """Links high-detail Credit Card offer (Amazon/Flipkart style)."""
# #     data = offer.model_dump()
# #     data["product_id"] = product_id
# #     result = await insert_one("credit_card_offers", data)
# #     return {"success": True, "data": result}

# # @router.post("/{product_id}/debit-card-offers", status_code=status.HTTP_201_CREATED)
# # async def add_debit_card_offer(
# #     product_id: str,
# #     offer: CardOfferBase,
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     """Links high-detail Debit Card offer."""
# #     data = offer.model_dump()
# #     data["product_id"] = product_id
# #     result = await insert_one("debit_card_offers", data)
# #     return {"success": True, "data": result}

# # @router.post("/{product_id}/emi-plans", status_code=status.HTTP_201_CREATED)
# # async def add_emi_plan(
# #     product_id: str,
# #     plan: EMIPlan,
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     """Adds a detailed tenure-based EMI plan with interest breakdown."""
# #     data = plan.model_dump()
# #     data["product_id"] = product_id
# #     result = await insert_one("emi_plans", data)
# #     return {"success": True, "data": result}

# # @router.post("/{product_id}/upi-offers", status_code=status.HTTP_201_CREATED)
# # async def add_upi_offer(
# #     product_id: str,
# #     offer: UPIOffer,
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     """Adds a UPI platform discount (PhonePe/GPay)."""
# #     data = offer.model_dump()
# #     data["product_id"] = product_id
# #     result = await insert_one("upi_offers", data)
# #     return {"success": True, "data": result}






















# # from fastapi import APIRouter, Depends, HTTPException, status
# # from typing import List
# # import logging

# # # Modular imports from your production structure
# # from app.db.supabase import (
# #     insert_one, select_all, select_one, update_one, delete_one, select_many
# # )
# # from app.dependencies import get_current_user, get_current_admin_user
# # from app.schemas.schemas import (
# #     ProductCreate, ProductUpdate, ProductResponse, ProductDetailResponse,
# #     CardOfferBase, EMIPlan, UPIOffer
# # )

# # # Setup logging
# # logger = logging.getLogger(__name__)
# # router = APIRouter()

# # # ============ PRODUCT READ OPERATIONS ============

# # @router.get("/", response_model=List[ProductResponse])
# # async def get_products(current_user: dict = Depends(get_current_user)):
# #     try:
# #         products = await select_all("products", {"branch_id": current_user["branch_id"]})
# #         return products
# #     except Exception as e:
# #         logger.error(f"Failed to fetch products: {str(e)}")
# #         return []

# # @router.get("/{product_id}/all-offers")
# # async def get_all_offers_consolidated(
# #     product_id: str, 
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     """
# #     FIX FOR 404: Consolidated fetch for the 'Live Inspector' in OfferManager.tsx.
# #     Gathers all payment types into one list with a 'type' tag for deletion.
# #     """
# #     # Verify product exists in branch
# #     product = await select_one("products", {"product_id": product_id, "branch_id": current_user["branch_id"]})
# #     if not product:
# #         raise HTTPException(status_code=404, detail="Product not found")

# #     all_offers = []

# #     # Fetch from all 4 tables
# #     cc = await select_many("credit_card_offers", {"product_id": product_id})
# #     dc = await select_many("debit_card_offers", {"product_id": product_id})
# #     emi = await select_many("emi_plans", {"product_id": product_id})
# #     upi = await select_many("upi_offers", {"product_id": product_id})

# #     # Normalize data for frontend display
# #     for o in cc: all_offers.append({**o, "type": "credit", "id": o.get("id")})
# #     for o in dc: all_offers.append({**o, "type": "debit", "id": o.get("id")})
# #     for o in emi: all_offers.append({**o, "type": "emi", "id": o.get("id"), "bank_name": o.get("institute_name"), "bank_logo_url": o.get("institute_logo_url")})
# #     for o in upi: all_offers.append({**o, "type": "upi", "id": o.get("id"), "bank_name": o.get("platform_name"), "bank_logo_url": o.get("platform_logo_url")})

# #     return all_offers

# # @router.get("/{product_id}", response_model=ProductDetailResponse)
# # async def get_product_details(product_id: str, current_user: dict = Depends(get_current_user)):
# #     product = await select_one("products", {"product_id": product_id, "branch_id": current_user["branch_id"]})
# #     if not product:
# #         raise HTTPException(status_code=404, detail="Product not found")

# #     product["credit_card_offers"] = await select_many("credit_card_offers", {"product_id": product_id})
# #     product["debit_card_offers"] = await select_many("debit_card_offers", {"product_id": product_id})
# #     product["emi_plans"] = await select_many("emi_plans", {"product_id": product_id})
# #     product["upi_offers"] = await select_many("upi_offers", {"product_id": product_id})
# #     return product

# # # ============ PRODUCT WRITE OPERATIONS ============

# # @router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
# # async def create_product(product_data: ProductCreate, current_user: dict = Depends(get_current_user)):
# #     data = product_data.model_dump()
# #     if "price" in data: data["price"] = int(round(data["price"]))
# #     data.update({"branch_id": current_user["branch_id"], "created_by": current_user["user_id"]})
# #     return await insert_one("products", data)

# # @router.put("/{product_id}", response_model=ProductResponse)
# # async def update_product(product_id: str, product_data: ProductUpdate, current_user: dict = Depends(get_current_user)):
# #     update_dict = product_data.model_dump(exclude_unset=True)
# #     if "price" in update_dict: update_dict["price"] = int(round(update_dict["price"]))
# #     return await update_one("products", {"product_id": product_id}, update_dict)

# # @router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
# # async def delete_product(product_id: str, current_user: dict = Depends(get_current_admin_user)):
# #     await delete_one("products", {"product_id": product_id})
# #     return None

# # # ============ FINANCIAL OFFER OPERATIONS (POST & DELETE) ============

# # @router.post("/{product_id}/credit-card-offers", status_code=201)
# # async def add_cc_offer(product_id: str, offer: CardOfferBase):
# #     data = offer.model_dump()
# #     data["product_id"] = product_id
# #     return await insert_one("credit_card_offers", data)

# # @router.delete("/{product_id}/credit-card-offers/{offer_id}")
# # async def delete_cc_offer(product_id: str, offer_id: str):
# #     return await delete_one("credit_card_offers", {"id": offer_id, "product_id": product_id})

# # @router.post("/{product_id}/debit-card-offers", status_code=201)
# # async def add_dc_offer(product_id: str, offer: CardOfferBase):
# #     data = offer.model_dump()
# #     data["product_id"] = product_id
# #     return await insert_one("debit_card_offers", data)

# # @router.delete("/{product_id}/debit-card-offers/{offer_id}")
# # async def delete_dc_offer(product_id: str, offer_id: str):
# #     return await delete_one("debit_card_offers", {"id": offer_id, "product_id": product_id})

# # @router.post("/{product_id}/emi-plans", status_code=201)
# # async def add_emi_plan(product_id: str, plan: EMIPlan):
# #     data = plan.model_dump()
# #     data["product_id"] = product_id
# #     return await insert_one("emi_plans", data)

# # @router.delete("/{product_id}/emi-plans/{plan_id}")
# # async def delete_emi_plan(product_id: str, plan_id: str):
# #     return await delete_one("emi_plans", {"id": plan_id, "product_id": product_id})

# # @router.post("/{product_id}/upi-offers", status_code=201)
# # async def add_upi_offer(product_id: str, offer: UPIOffer):
# #     data = offer.model_dump()
# #     data["product_id"] = product_id
# #     return await insert_one("upi_offers", data)

# # @router.delete("/{product_id}/upi-offers/{offer_id}")
# # async def delete_upi_offer(product_id: str, offer_id: str):
# #     return await delete_one("upi_offers", {"id": offer_id, "product_id": product_id})




































































# from fastapi import APIRouter, Depends, HTTPException, status
# from typing import List, Dict, Any, Optional
# import logging
# import math

# # Modular imports from your production structure
# from app.db.supabase import (
#     insert_one, select_all, select_one, update_one, delete_one, select_many
# )
# from app.dependencies import get_current_user, get_current_admin_user
# from app.schemas.schemas import (
#     ProductCreate, ProductUpdate, ProductResponse, ProductDetailResponse,
#     CardOfferBase, EMIPlan, UPIOffer
# )

# # Setup logging for production monitoring
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# router = APIRouter()

# # ============ HELPER UTILITIES ============

# def get_actual_id(o: Dict[str, Any]) -> Optional[str]:
#     """
#     Unified ID extractor that maps various SQL primary keys to a single 'id' 
#     for the React frontend to consume easily.
#     """
#     val = (
#         o.get("cc_offer_id") or      # Credit Card
#         o.get("dc_offer_id") or      # Debit Card
#         o.get("emi_plan_id") or      # EMI Plans
#         o.get("upi_offer_id") or     # UPI Offers
#         o.get("product_id") or       # Product Core
#         o.get("id")                  # Fallback
#     )
#     return str(val) if val is not None else None

# def validate_id(id_val: str):
#     """Safety check for ID validity to prevent 'undefined' string errors."""
#     if not id_val or str(id_val).lower() == "none" or str(id_val) == "undefined":
#         logger.warning(f"Invalid ID attempted: {id_val}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, 
#             detail="A valid Database ID is required for this operation."
#         )

# async def calculate_emi_details(product_id: str, plan_data: dict) -> dict:
#     """Core Financial Logic: Calculates EMI installments and totals."""
#     search_id = int(product_id) if product_id.isdigit() else product_id
#     product = await select_one("products", {"product_id": search_id})
    
#     if not product:
#         raise HTTPException(status_code=404, detail="Product not found for EMI calculation")
    
#     product_price = float(product.get("price", 0))
#     tenure = int(plan_data.get("tenure_months", 6))
#     interest_rate_pa = float(plan_data.get("interest_rate_pa", 0))
#     processing_fee = int(plan_data.get("processing_fee", 0))
#     is_no_cost = plan_data.get("is_no_cost_emi", False)

#     if is_no_cost:
#         monthly_installment = math.ceil(product_price / tenure)
#         total_repayment = (monthly_installment * tenure) + processing_fee
#         actual_interest = 0.0
#     else:
#         monthly_interest_rate = (interest_rate_pa / 12) / 100
#         if monthly_interest_rate > 0:
#             pow_factor = (1 + monthly_interest_rate) ** tenure
#             emi_numerator = product_price * monthly_interest_rate * pow_factor
#             emi_denominator = pow_factor - 1
#             monthly_installment = math.ceil(emi_numerator / emi_denominator)
#         else:
#             monthly_installment = math.ceil(product_price / tenure)
        
#         total_repayment = (monthly_installment * tenure) + processing_fee
#         actual_interest = interest_rate_pa

#     return {
#         "product_id": search_id,
#         "institute_name": plan_data.get("institute_name"),
#         "institute_logo_url": plan_data.get("institute_logo_url"),
#         "tenure_months": tenure,
#         "monthly_installment": monthly_installment,
#         "interest_rate_pa": actual_interest,
#         "total_repayment_amount": total_repayment,
#         "is_no_cost_emi": is_no_cost,
#         "processing_fee": processing_fee,
#         "min_purchase_amount": plan_data.get("min_purchase_amount", 0),
#         "offer_text": f"No-Cost EMI for {tenure}m" if is_no_cost else f"₹{monthly_installment}/mo for {tenure}m"
#     }

# # ============ PRODUCT CORE OPERATIONS ============

# @router.get("/", response_model=List[ProductResponse])
# async def get_products(current_user: dict = Depends(get_current_user)):
#     try:
#         return await select_all("products", {"branch_id": current_user["branch_id"]})
#     except Exception as e:
#         logger.error(f"Failed to fetch products: {str(e)}")
#         return []

# @router.post("/", status_code=status.HTTP_201_CREATED)
# async def create_product(
#     product: ProductCreate, 
#     current_user: dict = Depends(get_current_admin_user)
# ):
#     """
#     FIXED: Now injects 'branch_id' and 'created_by' from the authenticated session
#     to satisfy Supabase NOT NULL constraints.
#     """
#     try:
#         data = product.model_dump()
        
#         # Inject metadata from current_user session
#         data["branch_id"] = current_user["branch_id"]
#         data["created_by"] = current_user.get("user_id") # Resolves constraint 23502
        
#         logger.info(f"Creating product '{data['name']}' for branch {data['branch_id']} by user {data['created_by']}")
        
#         result = await insert_one("products", data)
#         return result
#     except Exception as e:
#         logger.error(f"Creation Error: {str(e)}")
#         raise HTTPException(
#             status_code=500, 
#             detail=f"Database insertion failed: {str(e)}"
#         )

# @router.put("/{product_id}")
# async def update_product_details(
#     product_id: str, 
#     update_data: ProductUpdate, 
#     current_user: dict = Depends(get_current_admin_user)
# ):
#     """
#     FIXED: Validates clean ID and ensures branch-level security.
#     """
#     validate_id(product_id)
#     payload = update_data.model_dump(exclude_unset=True)
    
#     if not payload:
#         raise HTTPException(status_code=400, detail="No valid update data provided.")

#     clean_id = int(product_id) if product_id.isdigit() else product_id

#     try:
#         filters = {"product_id": clean_id, "branch_id": current_user["branch_id"]}
#         logger.info(f"Updating product {clean_id} with data: {payload}")
        
#         result = await update_one("products", filters, payload)
#         if not result:
#             raise HTTPException(status_code=404, detail="Product not found or unauthorized.")
#         return result
#     except Exception as e:
#         logger.error(f"SUPABASE UPDATE ERROR: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Backend Update Failed: {str(e)}")

# @router.delete("/{product_id}")
# async def delete_product(product_id: str, current_user: dict = Depends(get_current_admin_user)):
#     validate_id(product_id)
#     clean_id = int(product_id) if product_id.isdigit() else product_id
#     return await delete_one("products", {"product_id": clean_id, "branch_id": current_user["branch_id"]})

# # ============ CONSOLIDATED OFFER VIEW ============

# @router.get("/{product_id}/all-offers")
# async def get_all_offers_consolidated(product_id: str, current_user: dict = Depends(get_current_user)):
#     clean_id = int(product_id) if product_id.isdigit() else product_id
    
#     product = await select_one("products", {"product_id": clean_id})
#     if not product:
#         raise HTTPException(status_code=404, detail="Product not found")

#     def normalize_offer(offer_list, offer_type):
#         normalized = []
#         for o in offer_list:
#             actual_id = get_actual_id(o)
#             if not actual_id: continue 
#             normalized.append({
#                 **o,
#                 "type": offer_type,
#                 "id": actual_id, 
#                 "display_name": o.get("bank_name") or o.get("institute_name") or o.get("platform_name"),
#                 "display_logo": o.get("bank_logo_url") or o.get("institute_logo_url") or o.get("platform_logo_url")
#             })
#         return normalized

#     cc = await select_many("credit_card_offers", {"product_id": clean_id})
#     dc = await select_many("debit_card_offers", {"product_id": clean_id})
#     emi = await select_many("emi_plans", {"product_id": clean_id})
#     upi = await select_many("upi_offers", {"product_id": clean_id})

#     return (normalize_offer(cc, "credit") + normalize_offer(dc, "debit") + 
#             normalize_offer(emi, "emi") + normalize_offer(upi, "upi"))

# # ============ FINANCIAL OFFER OPERATIONS ============

# @router.post("/{product_id}/credit-card-offers", status_code=201)
# async def add_cc_offer(product_id: str, offer: CardOfferBase):
#     clean_id = int(product_id) if product_id.isdigit() else product_id
#     data = offer.model_dump()
#     data["product_id"] = clean_id
#     return await insert_one("credit_card_offers", data)

# @router.put("/{product_id}/credit-card-offers/{offer_id}")
# async def update_cc_offer(product_id: str, offer_id: str, offer: CardOfferBase):
#     validate_id(offer_id)
#     p_id = int(product_id) if product_id.isdigit() else product_id
#     o_id = int(offer_id) if offer_id.isdigit() else offer_id
#     return await update_one("credit_card_offers", {"cc_offer_id": o_id, "product_id": p_id}, offer.model_dump())

# @router.post("/{product_id}/emi-plans", status_code=201)
# async def add_emi_plan(product_id: str, plan: EMIPlan):
#     db_ready_data = await calculate_emi_details(product_id, plan.model_dump())
#     return await insert_one("emi_plans", db_ready_data)

# @router.delete("/{product_id}/{route}/{offer_id}")
# async def generic_delete_offer(product_id: str, route: str, offer_id: str):
#     validate_id(offer_id)
#     p_id = int(product_id) if product_id.isdigit() else product_id
#     o_id = int(offer_id) if offer_id.isdigit() else offer_id
    
#     route_to_key = {
#         "credit-card-offers": "cc_offer_id",
#         "debit-card-offers": "dc_offer_id",
#         "emi-plans": "emi_plan_id",
#         "upi-offers": "upi_offer_id"
#     }
    
#     table_name = route.replace("-", "_")
#     key_column = route_to_key.get(route)
#     if not key_column:
#         raise HTTPException(status_code=400, detail="Invalid offer route.")
        
#     return await delete_one(table_name, {key_column: o_id, "product_id": p_id})
































































from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
import logging
import math

# Modular Database and Security imports
from app.db.supabase import (
    insert_one, select_all, select_one, update_one, delete_one, select_many
)
from app.dependencies import get_current_user, get_current_admin_user
from app.schemas.schemas import (
    ProductCreate, ProductUpdate, ProductResponse, ProductDetailResponse,
    CardOfferBase, EMIPlan, UPIOffer
)

# Production-grade logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# ============ HELPER UTILITIES ============

def get_actual_id(o: Dict[str, Any]) -> Optional[str]:
    """
    Unified ID extractor that maps various SQL primary keys to a single 'id' 
    for the React frontend. Handles all offer table variations.
    """
    val = (
        o.get("cc_offer_id") or      # Table: credit_card_offers
        o.get("dc_offer_id") or      # Table: debit_card_offers
        o.get("emi_plan_id") or      # Table: emi_plans
        o.get("upi_offer_id") or     # Table: upi_offers
        o.get("product_id") or       # Table: products
        o.get("id")                  # General Fallback
    )
    return str(val) if val is not None else None

def validate_id(id_val: str):
    """Prevents common frontend bugs like passing 'undefined' or 'null' as strings."""
    if not id_val or str(id_val).lower() in ["none", "undefined", "null"]:
        logger.error(f"Validation Failure: Received invalid ID {id_val}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="A valid Database ID is required. Received 'undefined' or 'null'."
        )

async def calculate_emi_details(product_id: str, plan_data: dict) -> dict:
    """
    Recalculates monthly installments and total repayment.
    Ensures financial data is accurate even if the interest rate or tenure changes.
    """
    search_id = int(product_id) if str(product_id).isdigit() else product_id
    product = await select_one("products", {"product_id": search_id})
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found for financial calculation")
    
    price = float(product.get("price", 0))
    tenure = int(plan_data.get("tenure_months", 6))
    interest_rate_pa = float(plan_data.get("interest_rate_pa", 0))
    fee = int(plan_data.get("processing_fee", 0))
    is_no_cost = plan_data.get("is_no_cost_emi", False)

    if is_no_cost:
        monthly_installment = math.ceil(price / tenure)
        total_repayment = (monthly_installment * tenure) + fee
        actual_interest = 0.0
    else:
        # Standard Amortization Formula for EMI
        monthly_rate = (interest_rate_pa / 12) / 100
        if monthly_rate > 0:
            pow_factor = (1 + monthly_rate) ** tenure
            monthly_installment = math.ceil((price * monthly_rate * pow_factor) / (pow_factor - 1))
        else:
            monthly_installment = math.ceil(price / tenure)
        
        total_repayment = (monthly_installment * tenure) + fee
        actual_interest = interest_rate_pa

    return {
        "product_id": search_id,
        "institute_name": plan_data.get("institute_name"),
        "institute_logo_url": plan_data.get("institute_logo_url"),
        "tenure_months": tenure,
        "monthly_installment": monthly_installment,
        "interest_rate_pa": actual_interest,
        "total_repayment_amount": total_repayment,
        "is_no_cost_emi": is_no_cost,
        "processing_fee": fee,
        "min_purchase_amount": plan_data.get("min_purchase_amount", 0),
        "offer_text": f"No-Cost EMI for {tenure}m" if is_no_cost else f"₹{monthly_installment}/mo for {tenure}m"
    }

# ============ PRODUCT CORE OPERATIONS ============

@router.get("/", response_model=List[ProductResponse])
async def get_products(current_user: dict = Depends(get_current_user)):
    """Fetches all products for the current branch."""
    return await select_all("products", {"branch_id": current_user["branch_id"]})

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate, current_user: dict = Depends(get_current_admin_user)):
    """Creates a product and links it to the logged-in admin's branch."""
    data = product.model_dump()
    data["branch_id"] = current_user["branch_id"]
    data["created_by"] = current_user.get("user_id") 
    return await insert_one("products", data)

@router.put("/{product_id}")
async def update_product_details(product_id: str, update_data: ProductUpdate, current_user: dict = Depends(get_current_admin_user)):
    """Updates product details within the same branch."""
    validate_id(product_id)
    payload = update_data.model_dump(exclude_unset=True)
    clean_id = int(product_id) if product_id.isdigit() else product_id
    filters = {"product_id": clean_id, "branch_id": current_user["branch_id"]}
    return await update_one("products", filters, payload)

@router.delete("/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(get_current_admin_user)):
    """Deletes a product from the branch inventory."""
    validate_id(product_id)
    clean_id = int(product_id) if product_id.isdigit() else product_id
    return await delete_one("products", {"product_id": clean_id, "branch_id": current_user["branch_id"]})

# ============ FINANCIAL OFFER OPERATIONS (FIXED 405s & 404s) ============

# --- 1. Credit Card Offers ---
@router.post("/{product_id}/credit-card-offers", status_code=201)
async def add_cc_offer(product_id: str, offer: CardOfferBase):
    data = offer.model_dump()
    data["product_id"] = int(product_id) if product_id.isdigit() else product_id
    return await insert_one("credit_card_offers", data)

@router.put("/{product_id}/credit-card-offers/{offer_id}")
async def update_cc_offer(product_id: str, offer_id: str, offer: CardOfferBase):
    validate_id(offer_id)
    p_id = int(product_id) if product_id.isdigit() else product_id
    o_id = int(offer_id) if offer_id.isdigit() else offer_id
    return await update_one("credit_card_offers", {"cc_offer_id": o_id, "product_id": p_id}, offer.model_dump())

# --- 2. Debit Card Offers ---
@router.post("/{product_id}/debit-card-offers", status_code=201)
async def add_dc_offer(product_id: str, offer: CardOfferBase):
    data = offer.model_dump()
    data["product_id"] = int(product_id) if product_id.isdigit() else product_id
    return await insert_one("debit_card_offers", data)

@router.put("/{product_id}/debit-card-offers/{offer_id}")
async def update_dc_offer(product_id: str, offer_id: str, offer: CardOfferBase):
    validate_id(offer_id)
    p_id = int(product_id) if product_id.isdigit() else product_id
    o_id = int(offer_id) if offer_id.isdigit() else offer_id
    return await update_one("debit_card_offers", {"dc_offer_id": o_id, "product_id": p_id}, offer.model_dump())

# --- 3. UPI Offers ---
@router.post("/{product_id}/upi-offers", status_code=201)
async def add_upi_offer(product_id: str, offer: UPIOffer):
    data = offer.model_dump()
    data["product_id"] = int(product_id) if product_id.isdigit() else product_id
    return await insert_one("upi_offers", data)

@router.put("/{product_id}/upi-offers/{offer_id}")
async def update_upi_offer(product_id: str, offer_id: str, offer: UPIOffer):
    validate_id(offer_id)
    p_id = int(product_id) if product_id.isdigit() else product_id
    o_id = int(offer_id) if offer_id.isdigit() else offer_id
    return await update_one("upi_offers", {"upi_offer_id": o_id, "product_id": p_id}, offer.model_dump())

# --- 4. EMI Plans ---
@router.post("/{product_id}/emi-plans", status_code=201)
async def add_emi_plan(product_id: str, plan: EMIPlan):
    db_ready_data = await calculate_emi_details(product_id, plan.model_dump())
    return await insert_one("emi_plans", db_ready_data)

@router.put("/{product_id}/emi-plans/{offer_id}")
async def update_emi_plan(product_id: str, offer_id: str, plan: EMIPlan):
    validate_id(offer_id)
    # Automatically recalculates installments if price or interest was changed
    db_ready_data = await calculate_emi_details(product_id, plan.model_dump())
    p_id = int(product_id) if product_id.isdigit() else product_id
    o_id = int(offer_id) if offer_id.isdigit() else offer_id
    return await update_one("emi_plans", {"emi_plan_id": o_id, "product_id": p_id}, db_ready_data)

# ============ CONSOLIDATED VIEWS & GENERIC DELETE ============

@router.get("/{product_id}/all-offers")
async def get_all_offers_consolidated(product_id: str):
    """Returns a unified list of all available offers for a product."""
    clean_id = int(product_id) if product_id.isdigit() else product_id
    
    def normalize_offer(offer_list, offer_type):
        return [{
            **o,
            "type": offer_type,
            "id": get_actual_id(o), 
            "display_name": o.get("bank_name") or o.get("institute_name") or o.get("platform_name"),
            "display_logo": o.get("bank_logo_url") or o.get("institute_logo_url") or o.get("platform_logo_url")
        } for o in offer_list if get_actual_id(o)]

    cc = await select_many("credit_card_offers", {"product_id": clean_id})
    dc = await select_many("debit_card_offers", {"product_id": clean_id})
    emi = await select_many("emi_plans", {"product_id": clean_id})
    upi = await select_many("upi_offers", {"product_id": clean_id})

    return (normalize_offer(cc, "credit") + normalize_offer(dc, "debit") + 
            normalize_offer(emi, "emi") + normalize_offer(upi, "upi"))

@router.delete("/{product_id}/{route}/{offer_id}")
async def generic_delete_offer(product_id: str, route: str, offer_id: str):
    """Unified delete route that maps frontend route-names to SQL tables."""
    validate_id(offer_id)
    p_id = int(product_id) if product_id.isdigit() else product_id
    o_id = int(offer_id) if offer_id.isdigit() else offer_id
    
    # Mapping frontend kebab-case routes to (Table Name, Primary Key Column)
    mapping = {
        "credit-card-offers": ("credit_card_offers", "cc_offer_id"),
        "debit-card-offers": ("debit_card_offers", "dc_offer_id"),
        "emi-plans": ("emi_plans", "emi_plan_id"),
        "upi-offers": ("upi_offers", "upi_offer_id")
    }
    
    if route not in mapping:
        raise HTTPException(status_code=400, detail="Invalid offer route.")
    
    table_name, key_column = mapping[route]
    return await delete_one(table_name, {key_column: o_id, "product_id": p_id})