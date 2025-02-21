from fastapi import FastAPI, HTTPException, Path, status, Response
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2 import IntegrityError
from psycopg2.extras import RealDictCursor
from datetime import date

# Initialize FastAPI app
app = FastAPI(
    title="Client Engagement API",
    description="API to manage and retrieve client engagement records.",
    version="1.0.0",
)

# Database connection details
DATABASE_CONFIG = {
    "dbname": "client_engagement",
    "user": "postgres",  # Replace with your PostgreSQL username
    "password": "000",  # Replace with your PostgreSQL password
    "host": "localhost",
    "port": "5432"
}

# Pydantic model for Client Engagement
class ClientEngagement(BaseModel):
    client_id: int
    client_name: str
    contact_email: str
    contact_phone: str
    signup_date: date
    engagement_type: str
    engagement_status: str
    last_meeting_date: date
    feedback_rating: int
    notes: str

    class Config:
        schema_extra = {
            "example": {
                "client_id": 1,
                "client_name": "Client A",
                "contact_email": "client_a@example.com",
                "contact_phone": "123-456-7890",
                "signup_date": date(2023, 10, 10),
                "engagement_type": "Consultation",
                "engagement_status": "Active",
                "last_meeting_date": date(2023, 10, 1),
                "feedback_rating": 4,
                "notes": "Very satisfied with the service."
            }
        }

# Function to connect to the database
def get_db_connection():
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# API endpoint to fetch all client engagement records
@app.get(
    "/client-engagements",
    response_model=List[ClientEngagement],
    summary="Get all client engagements",
    description="Retrieve a list of all client engagement records."
)
def get_client_engagements():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM client_engagement;")
        records = cursor.fetchall()
        return records
    except Exception as e:
        print(f"Error fetching records: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch records")
    finally:
        cursor.close()
        conn.close()

# API endpoint to fetch a single client engagement record by ID
@app.get(
    "/client-engagements/{client_id}",
    response_model=ClientEngagement,
    summary="Get a client engagement by ID",
    description="Retrieve a single client engagement record by its ID."
)
def get_client_engagement(
    client_id: int = Path(..., description="The ID of the client engagement to retrieve")
):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM client_engagement WHERE client_id = %s;", (client_id,))
        record = cursor.fetchone()
        if record:
            return ClientEngagement.parse_obj(record)
        else:
            raise HTTPException(status_code=404, detail="Client not found")
    except Exception as e:
        print(f"Error fetching record: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch record")
    finally:
        cursor.close()
        conn.close()


class ClientEngagementCreate(BaseModel):
    client_name: str
    contact_email: str
    contact_phone: str
    signup_date: date
    engagement_type: str
    engagement_status: str
    last_meeting_date: date
    feedback_rating: int
    notes: str

class ClientEngagementUpdate(BaseModel):
    client_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    signup_date: Optional[date] = None
    engagement_type: Optional[str] = None
    engagement_status: Optional[str] = None
    last_meeting_date: Optional[date] = None
    feedback_rating: Optional[int] = None
    notes: Optional[str] = None

# POST endpoint to create a new client engagement
@app.post(
    "/client-engagements",
    response_model=ClientEngagement,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new client engagement",
    description="Add a new client engagement record to the database."
)
def create_client_engagement(client: ClientEngagementCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO client_engagement (
                client_name, contact_email, contact_phone, 
                signup_date, engagement_type, engagement_status,
                last_meeting_date, feedback_rating, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *;
            """,
            (client.client_name, client.contact_email, client.contact_phone,
             client.signup_date, client.engagement_type, client.engagement_status,
             client.last_meeting_date, client.feedback_rating, client.notes)
        )
        new_client = cursor.fetchone()
        conn.commit()
        return new_client
    except IntegrityError as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error occurred"
        )
    except Exception as e:
        conn.rollback()
        print(f"Error creating client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create client engagement"
        )
    finally:
        cursor.close()
        conn.close()

# PUT endpoint to update an existing client engagement
@app.put(
    "/client-engagements/{client_id}",
    response_model=ClientEngagement,
    summary="Update a client engagement",
    description="Update an existing client engagement record by ID."
)
def update_client_engagement(
    client_id: int = Path(..., description="The ID of the client engagement to update"),
    client_update: ClientEngagementUpdate = ...
):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        updates = []
        values = []
        for field, value in client_update.dict(exclude_unset=True).items():
            updates.append(f"{field} = %s")
            values.append(value)
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update"
            )
        
        values.append(client_id)
        query = f"""
            UPDATE client_engagement
            SET {', '.join(updates)}
            WHERE client_id = %s
            RETURNING *;
        """
        cursor.execute(query, values)
        updated_client = cursor.fetchone()
        
        if not updated_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client engagement not found"
            )
        
        conn.commit()
        return updated_client
    except IntegrityError as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error occurred"
        )
    except Exception as e:
        conn.rollback()
        print(f"Error updating client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update client engagement"
        )
    finally:
        cursor.close()
        conn.close()

# DELETE endpoint to remove a client engagement
@app.delete(
    "/client-engagements/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a client engagement",
    description="Delete a client engagement record by ID."
)
def delete_client_engagement(
    client_id: int = Path(..., description="The ID of the client engagement to delete")
):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM client_engagement WHERE client_id = %s RETURNING *;",
            (client_id,)
        )
        deleted_client = cursor.fetchone()
        
        if not deleted_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client engagement not found"
            )
        
        conn.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        conn.rollback()
        print(f"Error deleting client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete client engagement"
        )
    finally:
        cursor.close()
        conn.close()