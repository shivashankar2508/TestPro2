#!/usr/bin/env python
from app.database import SessionLocal
from app.models.user import User

session = SessionLocal()
users = session.query(User).all()
print('Users in database:')
for user in users:
    print(f'  - ID: {user.id}, Email: {user.email}, Role: {user.role}, Active: {user.is_active}')
session.close()
