from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from datetime import datetime

app = FastAPI()

def init_db():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            balance REAL DEFAULT 0.0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            work_type TEXT,
            unit_count INTEGER,
            total_price REAL,
            created_at TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'Qabul qilindi',
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class ClientCreate(BaseModel):
    name: str
    phone: str

class OrderCreate(BaseModel):
    client_id: int
    work_type: str
    unit_count: int
    total_price: float
    deadline: str

@app.post("/clients/")
def add_client(client: ClientCreate):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO clients (name, phone) VALUES (?, ?)", (client.name, client.phone))
    conn.commit()
    conn.close()
    return {"message": "Mijoz qo'shildi"}

@app.get("/clients/")
def get_clients():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone, balance FROM clients")
    clients = cursor.fetchall()
    conn.close()
    # Formatlab ro'yxat qaytarish
    return [{"id": c[0], "name": c[1], "phone": c[2], "balance": c[3]} for c in clients]

@app.post("/orders/")
def create_order(order: OrderCreate):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    cursor.execute('''
        INSERT INTO orders (client_id, work_type, unit_count, total_price, created_at, deadline)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (order.client_id, order.work_type, order.unit_count, order.total_price, created_at, order.deadline))
    
    cursor.execute("UPDATE clients SET balance = balance + ? WHERE id = ?", (order.total_price, order.client_id))
    
    conn.commit()
    conn.close()
    return {"message": "Buyurtma ro'yxatga olindi"}

@app.get("/orders/")
def get_orders():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT orders.id, clients.name, orders.work_type, orders.unit_count, 
               orders.total_price, orders.created_at, orders.deadline, orders.status
        FROM orders
        JOIN clients ON orders.client_id = clients.id
        ORDER BY orders.id DESC
    ''')
    orders = cursor.fetchall()
    conn.close()
    return orders