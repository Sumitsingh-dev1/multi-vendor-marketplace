from fastapi import FastAPI,HTTPException,Depends,Header
from sqlalchemy import text
from app.schemas.customer import  CustomerCreate,LoginRequest,ProductCreate
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.customer import Customer,Product,UserRole
from fastapi import Depends
from app.core.config import settings
from app.database import engine
from app.core.security import hash_password,verify_password
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from app.core.jwt import create_access_token,decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jwt.exceptions import InvalidTokenError



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(
    title="Multi-Vendor Marketplace API",
    version="1.0.0"
)
security = HTTPBearer()


@app.get("/")
def home():
    return {
        "message": "Marketplace API is running"
    }


@app.get("/db-test")

def db_test():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), current_schema()")
        )
        row = result.fetchone()

    return {
        "database": row[0],
        "schema": row[1]
    }
@app.post("/customers")
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db)
):
    customer = Customer(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        phone=data.phone
    )
    try:
       db.add(customer)
       db.commit()
    except IntegrityError:
      db.rollback()
      raise HTTPException(
        status_code=409,
        detail="Email already registered"
    )
    return {"message": "Customer registered successfully"} 

@app.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    statement = select(Customer).where(
        Customer.email == data.email
    )

    customer = db.execute(statement).scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        data.password,
        customer.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token({
        "sub": str(customer.id)
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }
def get_current_customer(
    credentials: HTTPAuthorizationCredentials= Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
      raise HTTPException(
        status_code=401,
        detail="Invalid or expired token"
    )

    customer_id = payload.get("sub")

    if customer_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    statement = select(Customer).where(
        Customer.id == int(customer_id)
    )

    customer = db.execute(statement).scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=401,
            detail="Customer not found"
        )

    return customer
@app.get("/customers/me")
def get_my_profile(
    customer: Customer = Depends(get_current_customer)
):
    return {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone
    }
def require_seller(
    customer: Customer = Depends(get_current_customer)
):
    if customer.role != UserRole.SELLER:
        raise HTTPException(
            status_code=403,
            detail="Seller access required"
        )

    return customer
@app.post("/products")
def create_product(
    data: ProductCreate,
    customer: Customer = Depends(require_seller),
    db: Session = Depends(get_db)
):
    product = Product(
        name=data.name,
        description=data.description,
        price=data.price,
        stock=data.stock,
        seller_id=customer.id
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return {
        "message": "Product created successfully",
        "product_id": product.id
    }
