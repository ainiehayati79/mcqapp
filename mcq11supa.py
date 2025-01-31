import streamlit as st
import pandas as pd
import random
import hashlib
from supabase import create_client

# Initialize Supabase
supabase_url = "https://fqzoactudfcvoxxujves.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZxem9hY3R1ZGZjdm94eHVqdmVzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgzMjM1NTEsImV4cCI6MjA1Mzg5OTU1MX0.pTPSUtz7ZycBLf1o5N0eJ0HCsFH3MGxKfT8bshwXTmk"
supabase = create_client(supabase_url, supabase_key)

def check_password():
    """Verify admin password."""
    def password_entered():
        entered_password = str(st.session_state["password"]).strip()
        entered_hash = hashlib.sha256(entered_password.encode()).hexdigest()
        correct_hash = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"  # admin123
        if entered_hash == correct_hash:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.sidebar.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.sidebar.text_input("Password", type="password", on_change=password_entered, key="password")
        st.sidebar.error("😕 Password incorrect")
        return False
    else:
        return True

def admin_logout():
    """Handle admin logout."""
    if st.session_state.get("password_correct"):
        if st.sidebar.button("Logout"):
            st.session_state["password_correct"] = False
            st.rerun()

def initialize_session_state():
    """Initialize all session state variables."""
    if 'student_name' not in st.session_state:
        st.session_state.student_name = ""
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0
    if 'questions' not in st.session_state:
        st.session_state.questions = []
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {}
    if 'selected_answers' not in st.session_state:
        st.session_state.selected_answers = {}
    if 'attempts' not in st.session_state:
        st.session_state.attempts = {}
    if 'quiz_completed' not in st.session_state:
        st.session_state.quiz_completed = False
    if 'answer_submitted' not in st.session_state:
        st.session_state.answer_submitted = False

def load_questions_from_csv(file, category='General'):
    """Load questions from uploaded CSV file."""
    try:
        df = pd.read_csv(file)
        count = 0
        for _, row in df.iterrows():
            data = {
                'question': row['question'],
                'options': row['options'],
                'answer': row['answer'],
                'explanation': row['explaination'],
                'category': category
            }
            supabase.table('questions').insert(data).execute()
            count += 1
        return count
    except Exception as e:
        st.error(f"Error loading questions: {str(e)}")
        return 0

def fetch_questions():
    """Fetch all questions from database."""
    try:
        response = supabase.table('questions').select('*').execute()
        questions = []
        for row in response.data:
            questions.append({
                'question': row['question'],
                'options': row['options'].split(','),
                'answer': row['answer'],
                'explanation': row['explanation'],
                'category': row['category']
            })
        random.shuffle(questions)
        return questions
    except Exception as e:
        st.error(f"Error fetching questions: {str(e)}")
        return []

def save_quiz_result(student_name, score, total_questions, category='General'):
    """Save quiz results to database."""
    try:
        data = {
            'student_name': student_name,
            'score': score,
            'total_questions': total_questions,
            'category': category
        }
        supabase.table('performance').insert(data).execute()
    except Exception as e:
        st.error(f"Error saving results: {str(e)}")

def display_admin_panel():
    """Display and handle admin panel functionality."""
    st.sidebar.title("👨‍💼 Admin Panel")
    if check_password():
        st.sidebar.success("Welcome, Admin! 🔓")
        
        # File upload section
        uploaded_file = st.sidebar.file_uploader("Upload Questions (CSV)", type=['csv'])
        category = st.sidebar.text_input("Category", "General")
        
        if uploaded_file and st.sidebar.button("Add Questions"):
            count = load_questions_from_csv(uploaded_file, category)
            if count > 0:
                st.sidebar.success(f"Successfully added {count} questions!")
                st.rerun()
        
        # Add logout button
        admin_logout()

def handle_question_submission():
    """Handle the submission of a question answer."""
    current_q = st.session_state.questions[st.session_state.current_question_index]
    key = f"q_{st.session_state.current_question_index}"
    
    # Get the selected answer
    selected_answer = st.session_state.get(key)
    
    # Store the selected answer regardless of correctness
    st.session_state.selected_answers[st.session_state.current_question_index] = selected_answer
    
    # Initialize attempts for this question if not exists
    if key not in st.session_state.attempts:
        st.session_state.attempts[key] = 0
    
    # Debug information (optional - you can remove these in production)
    # st.write(f"Selected answer: {selected_answer}")
    # st.write(f"Correct answer: {current_q['answer']}")
    
    # Normalize both answers for comparison (strip whitespace and case)
    selected_normalized = selected_answer.strip().lower() if selected_answer else ""
    correct_normalized = current_q['answer'].strip().lower() if current_q['answer'] else ""
    
    # Check if answer is correct using normalized comparison
    if selected_normalized == correct_normalized:
        st.success("✅ Correct!")
        st.session_state.user_answers[st.session_state.current_question_index] = selected_answer
        st.session_state.answer_submitted = True
        return True
    else:
        st.session_state.attempts[key] += 1
        if st.session_state.attempts[key] >= 2:
            st.error("❌ Incorrect. Maximum attempts reached.")
            st.markdown(f"**Correct answer:** {current_q['answer']}")
            if current_q.get('explanation'):
                st.markdown(f"**Explanation:** {current_q['explanation']}")
            st.session_state.user_answers[st.session_state.current_question_index] = "incorrect"
            st.session_state.answer_submitted = True
            return True
        else:
            st.error("❌ Incorrect. Try again!")
            return False

def display_quiz():
    """Display the main quiz interface."""
    # Get current question
    current_q = st.session_state.questions[st.session_state.current_question_index]
    
    # Display question number and text
    st.subheader(f"Question {st.session_state.current_question_index + 1} of {len(st.session_state.questions)}")
    st.write(f"**{current_q['question']}**")
    
    # Display options with previously selected answer if it exists
    key = f"q_{st.session_state.current_question_index}"
    previous_answer = st.session_state.selected_answers.get(st.session_state.current_question_index)
    
    # Show radio buttons with options
    selected_option = st.radio(
        "Choose your answer:", 
        current_q['options'], 
        key=key,
        index=current_q['options'].index(previous_answer) if previous_answer in current_q['options'] else 0
    )
    
    # Submit and Next buttons in columns
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Submit Answer") and not st.session_state.answer_submitted:
            handle_question_submission()
            
    with col2:
        if st.session_state.answer_submitted:
            if st.button("Next Question"):
                if st.session_state.current_question_index < len(st.session_state.questions) - 1:
                    st.session_state.current_question_index += 1
                    st.session_state.answer_submitted = False
                    st.rerun()
                else:
                    st.session_state.quiz_completed = True
                    st.rerun()

def display_results():
    """Display quiz results."""
    st.success("🎉 Quiz Completed!")
    
    # Calculate score based on stored answers
    correct_answers = 0
    for i, q in enumerate(st.session_state.questions):
        selected = st.session_state.selected_answers.get(i, "").strip().lower()
        correct = q['answer'].strip().lower()
        if selected == correct:
            correct_answers += 1
    
    total_questions = len(st.session_state.questions)
    
    # Display score
    st.subheader("📊 Your Results")
    st.write(f"**Score:** {correct_answers} out of {total_questions}")
    percentage = (correct_answers / total_questions) * 100
    st.write(f"**Percentage:** {percentage:.1f}%")
    
    # Display answers review
    st.subheader("Review Your Answers")
    for i, q in enumerate(st.session_state.questions):
        st.write(f"**Question {i+1}:** {q['question']}")
        user_ans = st.session_state.selected_answers.get(i, "Not answered")
        correct_ans = q['answer']
        
        # Color code the answers
        if user_ans.strip().lower() == correct_ans.strip().lower():
            st.success(f"Your answer: {user_ans} ✅")
        else:
            st.error(f"Your answer: {user_ans} ❌")
            st.write(f"Correct answer: {correct_ans}")
        
        if user_ans.strip().lower() != correct_ans.strip().lower() and q.get('explanation'):
            st.info(f"Explanation: {q['explanation']}")
        st.write("---")

    
    # Save results
    save_quiz_result(st.session_state.student_name, correct_answers, total_questions)
    
    # Display celebratory animation for perfect score
    if correct_answers == total_questions:
        st.balloons()

def main():
    st.title("📚 MCQ Quiz System")
    
    # Initialize session state
    initialize_session_state()
    
    # Display admin panel
    display_admin_panel()
    
    # Handle student name input
    if not st.session_state.student_name:
        st.write("### Welcome to the Quiz! 👋")
        name = st.text_input("Please enter your name to begin:")
        if name:
            st.session_state.student_name = name
            st.session_state.questions = fetch_questions()
            st.rerun()
        return
    
    # Display quiz or results
    if not st.session_state.quiz_completed:
        if st.session_state.questions:
            display_quiz()
        else:
            st.warning("No questions available. Please contact the administrator.")
    else:
        display_results()
        if st.button("Start New Quiz"):
            # Reset session state for new quiz
            for key in list(st.session_state.keys()):
                if key not in ["password_correct"]:
                    del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()