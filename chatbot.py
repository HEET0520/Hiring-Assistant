import google.generativeai as genai
import re
from typing import Tuple, List, Dict, Any
import json
from database import DatabaseHandler
import random

class HiringAssistant:
    def __init__(self, api_key: str):
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
            self.db = DatabaseHandler()
        except Exception as e:
            print(f"ERROR: Could not initialize the assistant. Exception: {e}")
            raise e
        
        self.conversation_state = {
            'current_stage': 'greeting',
            'candidate_info': {},
            'tech_stack': [],
            'questions_asked': False,
            'technical_questions': [],
            'current_question_index': 0,
            'in_technical_questions': False,
            'candidate_id': None
        }
        
        self.chat = self.model.start_chat(history=[])
    
    def get_current_question(self) -> str:
        """Get the current question based on conversation state."""
        if self.conversation_state['current_stage'] == 'greeting':
            return "Hello! I'm the TalentScout Hiring Assistant. I'll help evaluate your profile for potential opportunities."
    
    def validate_email(self, email: str) -> bool:
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+'        
        return re.match(pattern, email) is not None
    
    def validate_phone(self, phone: str) -> bool:
        pattern = r'^\+?1?\d{9,15}$'
        return re.match(pattern, phone) is not None
    
    def validate_experience(self, experience: str) -> bool:
        try:
            years = float(experience)
            return 0 <= years <= 50
        except ValueError:
            return False
    
    def get_system_prompt(self) -> str:
        return """You are an intelligent Hiring Assistant for TalentScout, a recruitment agency specializing in technology placements. 
        Your role is to gather candidate information and assess their technical skills. Be professional, friendly, and focused on recruitment.
        Only ask one question at a time and wait for the user's response."""
    

    async def generate_tech_questions(self, tech_stack: List[str]) -> List[str]:
        questions = []
        
        prompt = """Generate exactly one technical interview question for {tech} that:
        - Is relevant to the candidate's experience
        - Should be medium level question
        - Theoretical or conceptual
        - Is specific and clear
        - Should be in 1-2 lines
        - Must be different from other questions
        - Return only the question without any additional text"""

        # Take only first 3 technologies from tech stack
        for tech in tech_stack[:3]:
            try:
                response = self.model.generate_content(prompt.format(tech=tech))
                question = response.text.strip()
                # Ensure we only get the first question if multiple are generated
                question = question.split('\n')[0].strip()
                questions.append(question)
            except Exception as e:
                print(f"Error generating question for {tech}: {e}")
                questions.append(f"Please explain your experience with {tech} and its practical applications.")

        return questions[:3]




    
    async def process_input(self, user_input: str) -> Tuple[str, bool]:
        print(f"DEBUG: Current stage before processing: {self.conversation_state['current_stage']}")
        
        # Handling technical questions separately
        if self.conversation_state['in_technical_questions']:
            return await self._handle_technical_questions(user_input)

        # Identify handler
        handlers = {
            'greeting': self._handle_greeting,
            'name': self._handle_name,
            'email': self._handle_email,
            'phone': self._handle_phone,
            'experience': self._handle_experience,
            'position': self._handle_position,
            'location': self._handle_location,
            'tech_stack': self._handle_tech_stack
        }

        handler = handlers.get(self.conversation_state['current_stage'])
        
        if handler:
            response, should_exit = await handler(user_input)
            
            print(f"DEBUG: Current stage after processing: {self.conversation_state['current_stage']}")
            return response, should_exit

        return "I apologize, but I've lost track of our conversation. Let's start over.", True

    async def _handle_greeting(self, _: str) -> Tuple[str, bool]:
        self.conversation_state['current_stage'] = 'name'
        return "Could you please share your full name?", False

    async def _handle_name(self, user_input: str) -> Tuple[str, bool]:
        cleaned_name = " ".join(user_input.strip().split())
        self.conversation_state['candidate_info']['name'] = cleaned_name
        self.conversation_state['current_stage'] = 'email'
        return f"Nice to meet you, {cleaned_name}! Could you please provide your email address?", False
    
    async def _handle_email(self, user_input: str) -> Tuple[str, bool]:
        if not self.validate_email(user_input):
            return "That doesn't seem to be a valid email address. Please try again.", False
            
        # Check if candidate already exists
        existing_candidate = self.db.get_candidate_by_email(user_input)
        if existing_candidate:
            return "It seems you've already interviewed with us. Our team will contact you about your application.", True
            
        self.conversation_state['candidate_info']['email'] = user_input
        self.conversation_state['current_stage'] = 'phone'
        
        # Save conversation to database
        if self.conversation_state.get('candidate_id'):
            self.db.save_conversation(
                self.conversation_state['candidate_id'],
                'user',
                user_input
            )
            
        return "Thank you! Now, please share your phone number.", False

    
    async def _handle_phone(self, user_input: str) -> Tuple[str, bool]:
        # Remove any non-digit characters to allow formats like (555) 123-4567
        digits_only = ''.join(filter(str.isdigit, user_input))
        
        # Check if the result is exactly 10 digits
        if len(digits_only) != 10:
            return "Please enter a valid 10-digit phone number.", False
        
        # Store the formatted phone number
        self.conversation_state['candidate_info']['phone'] = digits_only
        self.conversation_state['current_stage'] = 'experience'
        return "Great! How many years of experience do you have in the technology industry?", False
    
    async def _handle_experience(self, user_input: str) -> Tuple[str, bool]:
        if not self.validate_experience(user_input):
            return "Please enter a valid number of years (e.g., '5' or '2.5').", False
        self.conversation_state['candidate_info']['experience'] = float(user_input)
        self.conversation_state['current_stage'] = 'position'
        return "What position(s) are you interested in?", False
    
    async def _handle_position(self, user_input: str) -> Tuple[str, bool]:
        self.conversation_state['candidate_info']['position'] = user_input
        self.conversation_state['current_stage'] = 'location'
        return "What is your current location?", False
    
    async def _handle_location(self, user_input: str) -> Tuple[str, bool]:
        self.conversation_state['candidate_info']['location'] = user_input
        self.conversation_state['current_stage'] = 'tech_stack'
        return "Please list your tech stack (programming languages, frameworks, databases, tools). Separate each technology with a comma.", False
    
    async def _handle_tech_stack(self, user_input: str) -> Tuple[str, bool]:
        tech_stack = [tech.strip() for tech in user_input.split(',')]
        self.conversation_state['tech_stack'] = tech_stack
        
        # Save candidate information to database
        try:
            candidate_id = self.db.save_candidate(self.conversation_state['candidate_info'])
            self.conversation_state['candidate_id'] = candidate_id
            
            # Save tech stack
            self.db.save_tech_stack(candidate_id, tech_stack)
            
            # Generate and save questions
            questions = await self.generate_tech_questions(tech_stack)
            self.conversation_state['technical_questions'] = questions
            self.conversation_state['answers'] = []
            self.conversation_state['in_technical_questions'] = True
            self.conversation_state['current_question_index'] = 0
            
            return f"Technical Assessment\n\nQuestion 1: {questions[0]}", False
            
        except Exception as e:
            print(f"Error saving candidate data: {str(e)}")
            return "I apologize, but there was an error saving your information. Please try again later.", True

    

    async def _handle_technical_questions(self, user_input: str) -> Tuple[str, bool]:
        current_index = self.conversation_state['current_question_index']
        self.conversation_state['answers'].append(user_input)
        next_index = current_index + 1
        self.conversation_state['current_question_index'] = next_index

        # Save the answer to database
        if self.conversation_state.get('candidate_id'):
            try:
                self.db.save_conversation(
                    self.conversation_state['candidate_id'],
                    'user',
                    user_input
                )
            except Exception as e:
                print(f"Error saving conversation: {str(e)}")

        if next_index < len(self.conversation_state['technical_questions']):
            return f"Question {next_index + 1}: {self.conversation_state['technical_questions'][next_index]}", False
        
        # Save complete assessment
        try:
            self.db.save_assessment(
                self.conversation_state['candidate_id'],
                self.conversation_state['technical_questions'],
                self.conversation_state['answers']
            )
        except Exception as e:
            print(f"Error saving assessment: {str(e)}")
            
        return "Technical assessment complete. Our team will review your responses.", True



# from transformers import pipeline
# from transformers import AutoModelForCausalLM, AutoTokenizer
# import re
# import json
# from typing import Tuple, List, Dict, Any
# import torch
# class HiringAssistant:
#     def __init__(self, api_key: str):
#         self.model_name = "Salesforce/codegen-350M-mono"
#         self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
#         self.model = AutoModelForCausalLM.from_pretrained(
#             self.model_name,
#             device_map="cpu",
#             trust_remote_code=True,
#         )
        
#         self.conversation_state = {
#             'current_stage': 'greeting', 
#             'candidate_info': {},
#             'tech_stack': [],
#             'questions_asked': False,
#             'technical_questions': [],
#             'current_question_index': 0,
#             'in_technical_questions': False
#         }
        
          
#     def get_current_question(self) -> str:
#         """Get the current question based on conversation state."""
#         if self.conversation_state['current_stage'] == 'greeting':
#             return "Hello! I'm the TalentScout Hiring Assistant. I'll help evaluate your profile for potential opportunities."
        
#     def _handle_greeting(self, _: str) -> Tuple[str, bool]:
#         self.conversation_state['current_stage'] = 'name'
#         return "Could you please share your full name?", False

#     def validate_email(self, email: str) -> bool:
#         pattern = r'^[\w\.-]+@[\w\.-]+\.\w+'        
#         return re.match(pattern, email) is not None
    
#     def validate_phone(self, phone: str) -> bool:
#         pattern = r'^\+?1?\d{9,15}$'
#         return re.match(pattern, phone) is not None
    
#     def validate_experience(self, experience: str) -> bool:
#         try:
#             years = float(experience)
#             return 0 <= years <= 50
#         except ValueError:
#             return False
    
#     def get_system_prompt(self) -> str:
#         return """You are an intelligent Hiring Assistant for TalentScout, a recruitment agency specializing in technology placements. 
#         Your role is to gather candidate information and assess their technical skills. Be professional, friendly, and focused on recruitment.
#         Only ask one question at a time and wait for the user's response."""
    
    
#     def generate_tech_questions(self, tech_stack: List[str]) -> List[str]:
#         if self.tokenizer.pad_token is None:
#             self.tokenizer.pad_token = self.tokenizer.eos_token
            
#         questions = []
#         if isinstance(tech_stack, str):
#             tech_stack = [t.strip() for t in tech_stack.split(',')]
            
#         prompt = """Write a clear, specific technical interview question. The question should:
#     - Start with 'What', 'How', 'Explain', or 'Describe'
#     - Focus on practical implementation
#     - Ask about a specific concept or problem
#     - Be 1-2 sentences long

#     Examples:
#     - What are the key differences between promises and async/await in JavaScript?
#     - How would you optimize database queries in a large-scale application?
#     - Explain how dependency injection works and its benefits.
#     """
        
#         for tech in tech_stack[:3]:
#             full_prompt = f"{prompt}\nGenerate a question about {tech}:"
            
#             inputs = self.tokenizer(
#                 full_prompt,
#                 return_tensors="pt",
#                 padding=True,
#                 truncation=True,
#                 max_length=1024
#             )
            
#             outputs = self.model.generate(
#                 input_ids=inputs["input_ids"],
#                 attention_mask=inputs["attention_mask"],
#                 max_length=1024,
#                 min_length=30,
#                 num_return_sequences=1,
#                 temperature=0.6,
#                 top_p=0.9,
#                 do_sample=True,
#                 pad_token_id=self.tokenizer.pad_token_id,
#                 eos_token_id=self.tokenizer.eos_token_id
#             )
            
#             question = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
#             questions.append(question.strip())
                
#         return questions
    
#     def process_input(self, user_input: str) -> Tuple[str, bool]:
#         print(f"DEBUG: Current stage before processing: {self.conversation_state['current_stage']}")
        
      
#         # Handling technical questions separately
#         if self.conversation_state['in_technical_questions']:
#             return self._handle_technical_questions(user_input)

#         # Identify handler
#         handlers = {
#             'greeting': self._handle_greeting,
#             'name': self._handle_name,
#             'email': self._handle_email,
#             'phone': self._handle_phone,
#             'experience': self._handle_experience,
#             'position': self._handle_position,
#             'location': self._handle_location,
#             'tech_stack': self._handle_tech_stack
#         }

#         handler = handlers.get(self.conversation_state['current_stage'])
        
#         if handler:
#             response, should_exit = handler(user_input)
            
#             print(f"DEBUG: Current stage after processing: {self.conversation_state['current_stage']}")
#             return response, should_exit

#         return "I apologize, but I've lost track of our conversation. Let's start over.", True

#     def _handle_exit(self) -> Tuple[str, bool]:
#         return "Thank you for your time! Our recruitment team will review your profile and contact you if there's a match. Good luck!", True
    
#     def _handle_greeting(self, _: str) -> Tuple[str, bool]:
#         # After greeting, move to the next stage
#         self.conversation_state['current_stage'] = 'name'
#         return "Could you please share your full name?", False

#     def _handle_name(self, user_input: str) -> Tuple[str, bool]:
#         # Normalize input (trim spaces)
#         cleaned_name = " ".join(user_input.strip().split())

#         # Store the name in the state
#         self.conversation_state['candidate_info']['name'] = cleaned_name
        
#         # Move to email stage
#         self.conversation_state['current_stage'] = 'email'

#         return f"Nice to meet you, {cleaned_name}! Could you please provide your email address?", False


    
#     def _handle_email(self, user_input: str) -> Tuple[str, bool]:
#         if not self.validate_email(user_input):
#             return "That doesn't seem to be a valid email address. Please try again.", False
#         self.conversation_state['candidate_info']['email'] = user_input
#         self.conversation_state['current_stage'] = 'phone'
#         return "Thank you! Now, please share your phone number.", False
    
#     def _handle_phone(self, user_input: str) -> Tuple[str, bool]:
#         if not self.validate_phone(user_input):
#             return "That doesn't seem to be a valid phone number. Please try again.", False
#         self.conversation_state['candidate_info']['phone'] = user_input
#         self.conversation_state['current_stage'] = 'experience'
#         return "Great! How many years of experience do you have in the technology industry?", False
    
#     def _handle_experience(self, user_input: str) -> Tuple[str, bool]:
#         if not self.validate_experience(user_input):
#             return "Please enter a valid number of years (e.g., '5' or '2.5').", False
#         self.conversation_state['candidate_info']['experience'] = float(user_input)
#         self.conversation_state['current_stage'] = 'position'
#         return "What position(s) are you interested in?", False
    
#     def _handle_position(self, user_input: str) -> Tuple[str, bool]:
#         self.conversation_state['candidate_info']['position'] = user_input
#         self.conversation_state['current_stage'] = 'location'
#         return "What is your current location?", False
    
#     def _handle_location(self, user_input: str) -> Tuple[str, bool]:
#         self.conversation_state['candidate_info']['location'] = user_input
#         self.conversation_state['current_stage'] = 'tech_stack'
#         return "Please list your tech stack (programming languages, frameworks, databases, tools). Separate each technology with a comma.", False
    
#     def _handle_tech_stack(self, user_input: str) -> Tuple[str, bool]:
#         # Process tech stack input
#         tech_stack = [tech.strip() for tech in user_input.split(',')]
#         self.conversation_state['tech_stack'] = tech_stack
        
#         # Generate questions and store them
#         self.conversation_state['technical_questions'] = self.generate_tech_questions(tech_stack)
        
#         # Set up for first question
#         self.conversation_state['in_technical_questions'] = True
#         self.conversation_state['current_question_index'] = 0
        
#         return f"Let's begin the technical assessment.\n\nQuestion 1: {self.conversation_state['technical_questions'][0]}", False


#     def _handle_technical_questions(self, user_input: str) -> Tuple[str, bool]:
#         # Store the previous answer
#         current_index = self.conversation_state['current_question_index']
#         self.conversation_state['answers'] = self.conversation_state.get('answers', [])
#         self.conversation_state['answers'].append(user_input)
        
#         # Move to next question
#         next_index = current_index + 1
#         self.conversation_state['current_question_index'] = next_index
        
#         # Check if we have more questions
#         if next_index < len(self.conversation_state['technical_questions']):
#             return f"Question {next_index + 1}: {self.conversation_state['technical_questions'][next_index]}", False
        
#         return "Thank you for completing the assessment. Our team will review your responses.", True