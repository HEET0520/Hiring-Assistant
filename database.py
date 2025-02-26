# database.py
from supabase import create_client
import os
from datetime import datetime
from dotenv import load_dotenv
import json
import streamlit as st

class DatabaseHandler:
    def __init__(self):
        
        supabase_url = st.secrets.get("SUPABASE_URL")
        supabase_key = st.secrets.get("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            st.warning("⚠️ Supabase credentials not found. Please set them in `.streamlit/secrets.toml`.")
            return  # Prevents app from breaking

        self.supabase = create_client(supabase_url, supabase_key)
        
    def save_candidate(self, candidate_info: dict) -> int:
        """Save candidate information and return candidate_id"""
        try:
            result = self.supabase.table('candidates').insert({
                'name': candidate_info.get('name'),
                'email': candidate_info.get('email'),
                'phone': candidate_info.get('phone'),
                'experience': float(candidate_info.get('experience', 0)),
                'position': candidate_info.get('position'),
                'location': candidate_info.get('location'),
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            
            return result.data[0]['id']
            
        except Exception as e:
            print(f"Error saving candidate: {str(e)}")
            raise
            
    def save_tech_stack(self, candidate_id: int, tech_stack: list):
        """Save candidate's tech stack"""
        try:
            tech_data = [{'candidate_id': candidate_id, 'technology': tech} 
                        for tech in tech_stack]
            
            self.supabase.table('tech_stack').insert(tech_data).execute()
            
        except Exception as e:
            print(f"Error saving tech stack: {str(e)}")
            raise
            
    def save_assessment(self, candidate_id: int, questions: list, answers: list):
        """Save technical assessment results"""
        try:
            assessment_data = []
            for q, a in zip(questions, answers):
                assessment_data.append({
                    'candidate_id': candidate_id,
                    'question': q,
                    'answer': a,
                    'created_at': datetime.utcnow().isoformat()
                })
                
            self.supabase.table('technical_assessments').insert(assessment_data).execute()
            
        except Exception as e:
            print(f"Error saving assessment: {str(e)}")
            raise
            
    def save_conversation(self, candidate_id: int, role: str, message: str):
        """Save conversation history"""
        try:
            self.supabase.table('conversation_history').insert({
                'candidate_id': candidate_id,
                'role': role,
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }).execute()
            
        except Exception as e:
            print(f"Error saving conversation: {str(e)}")
            raise
            
    def get_candidate_by_email(self, email: str):
        """Retrieve candidate information by email"""
        try:
            result = self.supabase.table('candidates')\
                .select('*')\
                .eq('email', email)\
                .execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error retrieving candidate: {str(e)}")
            raise
