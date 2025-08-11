from db.database import SessionLocal
from models import Client

def add_company_to_db(company_data):
    session = SessionLocal()
    try:
        company = Client(
            company_name=company_data.company_name,
            timezone=company_data.timezone,
            logo_url=company_data.logo_url
        )
        session.add(company)
        session.commit()
        session.refresh(company)
        return company
    finally:
        session.close()

def get_companies_from_db():
    session = SessionLocal()
    try:
        return session.query(Client).all()
    finally:
        session.close()



def get_company_by_id(company_id: int):
    session = SessionLocal()
    try:
        return session.query(Client).filter(Client.id == company_id).first()
    finally:
        session.close()

def update_company_in_db(company_id: int, company_data):
    session = SessionLocal()
    try:
        company = session.query(Client).filter(Client.id == company_id).first()
        if not company:
            return None
        
        if company_data.company_name is not None:
            company.company_name = company_data.company_name
        if company_data.timezone is not None:
            company.timezone = company_data.timezone
        if company_data.logo_url is not None:
            company.logo_url = company_data.logo_url
        
        session.commit()
        session.refresh(company)
        return company
    finally:
        session.close()
