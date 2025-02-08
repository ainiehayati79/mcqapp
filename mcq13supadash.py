import streamlit as st
import pandas as pd
import random
import hashlib
from supabase import create_client
from datetime import datetime

# Direct Supabase initialization (this worked in your test)
supabase_url = "https://fqzoactudfcvoxxujves.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZxem9hY3R1ZGZjdm94eHVqdmVzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgzMjM1NTEsImV4cCI6MjA1Mzg5OTU1MX0.pTPSUtz7ZycBLf1o5N0eJ0HCsFH3MGxKfT8bshwXTmk"

# Initialize Supabase client
supabase = create_client(supabase_url, supabase_key)

def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        entered_password = str(st.session_state["password"]).strip()
        entered_hash = hashlib.sha256(entered_password.encode()).hexdigest()
        correct_hash = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"  # admin123
        
        if entered_hash == correct_hash:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # Add a title for admin section
    st.sidebar.markdown("### 👨‍💼 Admin Access")
    st.sidebar.markdown("*Enter password to access admin features*")
    
    if "password_correct" not in st.session_state:
        st.sidebar.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.sidebar.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        
        return False
    else:
        return True


def add_questions_from_csv(file, category='General'):
    try:
        df = pd.read_csv(file)
        added_count = 0
        
        for _, row in df.iterrows():
            # Insert question into Supabase
            data = {
                'question': row['question'],
                'options': row['options'],
                'answer': row['answer'],
                'explanation': row['explainations'],
                'category': category
            }
            
            supabase.table('questions').insert(data).execute()
            added_count += 1
        
        return added_count
    except Exception as e:
        st.sidebar.error(f"Error adding questions: {str(e)}")
        return 0

def get_question_count():
    try:
        response = supabase.table('questions').select('count', count='exact').execute()
        return response.count
    except Exception as e:
        st.error(f"Error getting question count: {str(e)}")
        return 0


def handle_question_submission():
    """Handle the submission of a question answer."""
    current_q = st.session_state.questions[st.session_state.current_question_index]
    key = f"q_{st.session_state.current_question_index}"
    
    # Get the selected answer
    selected_answer = st.session_state.get(key)
    
    # Initialize attempts for this question if not exists
    if key not in st.session_state.attempts:
        st.session_state.attempts[key] = 0
    
    # Check if answer is correct
    if selected_answer == current_q['answer']:
        st.success("✅ Correct!")
        st.session_state.user_answers[st.session_state.current_question_index] = selected_answer
        st.session_state.answer_submitted = True
        return True
    else:
        st.session_state.attempts[key] += 1
        if st.session_state.attempts[key] >= 2:
            st.error("❌ Incorrect. Maximum attempts reached.")
            st.markdown(f"**Correct answer:** {current_q['answer']}")
            st.markdown(f"**Explanation:** {current_q['explanation']}")
            st.session_state.user_answers[st.session_state.current_question_index] = "incorrect"
            st.session_state.answer_submitted = True
            return True
        else:
            st.error("❌ Incorrect. Try again!")
            return False
        
def get_all_questions(category=None):
    try:
        if category and category != "All Categories":
            response = supabase.table('questions').select('*').eq('category', category).execute()
        else:
            response = supabase.table('questions').select('*').execute()
        
        questions = []
        for row in response.data:
            questions.append({
                "question": row['question'],
                "options": row['options'].split(','),
                "answer": row['answer'],
                "explanation": row['explanation'],
                "category": row['category']
            })
        return questions
    except Exception as e:
        st.error(f"Error fetching questions: {str(e)}")
        return []

def get_student_records():
    try:
        # Get all records, ordered by most recent first
        response = supabase.table('performance').select('*').order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching student records: {str(e)}")
        return []

def get_student_practice_summary():
    try:
        response = supabase.table('performance').select('*').execute()
        data = response.data
        
        # Create practice summary by student
        practice_summary = {}
        for record in data:
            student = record['student_name']
            if student not in practice_summary:
                practice_summary[student] = {
                    'practice_count': 0,
                    'best_score': 0,
                    'recent_score': 0,
                    'all_scores': [],  # Keep track of all scores for progress
                    'last_practice': record['created_at']
                }
            
            summary = practice_summary[student]
            percentage = (record['score'] / record['total_questions']) * 100
            
            summary['practice_count'] += 1
            summary['all_scores'].append(percentage)
            summary['best_score'] = max(summary['best_score'], percentage)
            
            # Update most recent practice score
            if record['created_at'] > summary['last_practice']:
                summary['recent_score'] = percentage
                summary['last_practice'] = record['created_at']
        
        return practice_summary
    except Exception as e:
        st.error(f"Error getting practice summary: {str(e)}")
        return {}

def display_practice_summary():
    st.subheader("Student Practice Summary")
    summary = get_student_practice_summary()
    if summary:
        summary_data = []
        for student, stats in summary.items():
            improvement = ""
            if len(stats['all_scores']) > 1:
                first_score = stats['all_scores'][0]
                latest_score = stats['recent_score']
                diff = latest_score - first_score
                improvement = f"{'+' if diff >= 0 else ''}{diff:.1f}%"
            
            summary_data.append({
                'Student': student,
                'Practice Sessions': stats['practice_count'],
                'Best Score': f"{stats['best_score']:.1f}%",
                'Recent Score': f"{stats['recent_score']:.1f}%",
                'Improvement': improvement
            })
        
        df = pd.DataFrame(summary_data)
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True
        )
        
        # Add download button for summary
        st.download_button(
            "Download Summary",
            df.to_csv(index=False).encode('utf-8'),
            "practice_summary.csv",
            "text/csv"
        )

def display_practice_history():
    st.subheader("Practice History")
    records = get_student_records()
    if records:
        df = pd.DataFrame(records)
        df['Date & Time'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        df['Score %'] = (df['score'] / df['total_questions'] * 100).round(1)
        df = df[['student_name', 'Score %', 'category', 'Date & Time']]
        df.columns = ['Student', 'Score %', 'Category', 'Practice Date']
        
        # Add filters
        col1, col2 = st.columns(2)
        with col1:
            selected_student = st.selectbox(
                "Filter by Student",
                ["All Students"] + list(df['Student'].unique())
            )
        with col2:
            selected_category = st.selectbox(
                "Filter by Category",
                ["All Categories"] + list(df['Category'].unique())
            )
        
        # Apply filters
        if selected_student != "All Students":
            df = df[df['Student'] == selected_student]
        if selected_category != "All Categories":
            df = df[df['Category'] == selected_category]
        
        st.dataframe(
            df.sort_values('Practice Date', ascending=False),
            hide_index=True,
            use_container_width=True
        )
        
        # Add download button for history
        st.download_button(
            "Download History",
            df.to_csv(index=False).encode('utf-8'),
            "practice_history.csv",
            "text/csv"
        )

def display_admin_dashboard():
    st.title("👨‍💼 Admin Dashboard")
    
    # Statistics cards in a row
    col1, col2, col3, col4 = st.columns(4)
    
    question_count = get_question_count()
    attempts, avg_score, max_score = get_performance_stats()
    
    with col1:
        st.metric("Total Questions", question_count)
    with col2:
        st.metric("Total Attempts", attempts)
    with col3:
        st.metric("Average Score", f"{avg_score:.1f}%")
    with col4:
        st.metric("Highest Score", f"{max_score:.1f}%")
    
    # Upload section
    st.divider()
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload questions (CSV)", type=["csv"])
    with col2:
        category = st.text_input("Category", "General")
        if uploaded_file and st.button("Add Questions"):
            added_count = add_questions_from_csv(uploaded_file, category)
            if added_count > 0:
                st.success(f"Added {added_count} questions!")
                st.rerun()
    
    # Practice Summary and History in tabs
    tab1, tab2 = st.tabs(["Practice Summary", "Practice History"])
    
    with tab1:
        display_practice_summary()
    
    with tab2:
        display_practice_history()

#lagibaru
def display_quiz(is_battle_mode=False):
    """Display quiz interface with proper answer validation."""
    st.title("📚 BattleQuix: MCQ Quiz!")
    
    if not st.session_state.student_name:
        st.info("Please enter your name in the sidebar to begin!")
        return
    
    st.subheader("Welcome to the Quiz!")
    
    # Category selection
    categories = get_categories()
    category_key = "category_select_battle" if is_battle_mode else "category_select"
    selected_category = st.selectbox(
        "Select Category:",
        categories,
        key=category_key
    )
    
    # Load and shuffle questions
    if (selected_category != st.session_state.selected_category or 
        not st.session_state.questions):
        st.session_state.selected_category = selected_category
        st.session_state.questions = get_all_questions(selected_category)
        if st.session_state.questions:
            shuffle_questions()
            st.rerun()
    
    if not st.session_state.questions:
        st.info("No questions available. Please select another category or ask an administrator to add questions.")
        return
    
    # Display questions
    for i, q in enumerate(st.session_state.shuffled_questions):
        st.subheader(f"Question {i+1}")
        st.markdown(f"**{q['question']}**")
        
        key = f"q_battle_{i}" if is_battle_mode else f"q_{i}"
        if not st.session_state.submitted:
            user_answer = st.radio(
                "Select your answer:",
                q['options'],
                key=key,
                index=None
            )
            st.session_state.user_answers[i] = user_answer
        else:
            # Show submitted answers
            user_answer = st.session_state.user_answers.get(i)
            if user_answer:
                is_correct = handle_answer_validation(user_answer, q['answer'])
                st.radio(
                    "Your answer:",
                    q['options'],
                    key=f"{key}_submitted",
                    index=q['options'].index(user_answer),
                    disabled=True
                )
                if is_correct:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Incorrect. Correct answer: {q['answer']}")
                    st.info(f"Explanation: {q['explanation']}")
    
    # Submit button
    btn_prefix = "battle_" if is_battle_mode else ""
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 New Quiz", key=f"{btn_prefix}new_quiz"):
            st.session_state.questions = []
            st.session_state.submitted = False
            st.session_state.user_answers = {}
            st.rerun()
    
    if not st.session_state.submitted:
        with col2:
            if st.button("📤 Submit Answers", key=f"{btn_prefix}submit"):
                if all(st.session_state.user_answers.values()):
                    st.session_state.submitted = True
                    st.rerun()
                else:
                    st.error("Please answer all questions before submitting.")
    
    # Show results
    if st.session_state.submitted:
        st.divider()
        st.subheader("📊 Results")
        
        score = sum(1 for i, q in enumerate(st.session_state.shuffled_questions) 
                   if handle_answer_validation(st.session_state.user_answers.get(i), q['answer']))
        
        st.success(f"**Final Score: {score}/{len(st.session_state.questions)}**")
        
        # Save performance only in regular mode and if not already submitted
        if not is_battle_mode and not st.session_state.get('score_saved', False):
            if save_performance(
                st.session_state.student_name,
                score,
                len(st.session_state.questions),
                selected_category
            ):
                st.session_state.score_saved = True  # Mark as saved
        
        if score == len(st.session_state.questions):
            st.balloons()
        
        return score
    
  

def main():
    # Initialize states
    initialize_quiz()
    initialize_battle_state()
    
    st.sidebar.image("BattleQuix.jpg", use_column_width=True)
    # Handle all user-related UI in sidebar
    with st.sidebar:
        if not st.session_state.student_name:
            st.title("👋 Welcome!")
            name_input = st.text_input("Enter your name to begin:")
            if name_input:
                st.session_state.student_name = name_input
                st.rerun()
        else:
            st.write(f"👤 Student: {st.session_state.student_name}")
            if st.button("Sign Out", use_container_width=True):
                sign_out()
                st.rerun()
        st.divider()
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Quiz", 
        "📊 Admin Dashboard", 
        "🥇Leader Board",
        "⚔️ Battle Arena",
        "📮 Feedback"
    ])
    
    with tab1:
        display_quiz()
    
    with tab2:
        if check_password():
            st.sidebar.success("Welcome, Admin! 🔓")
            display_admin_dashboard()
            admin_logout()
        else:
            st.title("Admin Dashboard")
            st.info("Please log in as admin to view the dashboard.")
    
    with tab3:
        st.title("🏆 Leaderboard")
        display_leaderboard()
    
    with tab4:
        if not st.session_state.student_name:
            st.info("Please enter your name in the sidebar to start a battle!")
        else:
            st.title("⚔️ Battle Arena")
            display_battle_tab()
            
    with tab5:
        st.title("📮 Feedback")
        show_user_feedback_page()

 
 
  # Footer (appears on all pages)
    #st.markdown("""<div style='text-align: center; margin-top: 50px;'>
    #<p style='font-size: 14px;'><b>iPTutor: Developed by [Ts. Ainie Hayati Noruzman][ainie_hayati@psis.edu.my]©[2024]</p>""", unsafe_allow_html=True)
    
    
    st.markdown(
    """ <div style='text-align: center; background-color: #592442; padding: 2px; border: 2px solid #A6A6A6; border-radius: 5px; margin-top: 15px;'>
    <p style='color: white;'>© 2024 BattleQuix: Learn, Compete, Conquer!". All rights reserved.</p>
    </div>
    """,
    unsafe_allow_html=True
)
 
# When leaving battle room:
def leave_battle_room(room_id, is_creator):
    """Handle leaving the battle room."""
    try:
        data = {
            'status': 'completed',
            'left_by': 'creator' if is_creator else 'joiner'
        }
        response = supabase.table('battle_rooms').update(data).eq('id', room_id).execute()
        if response.data:
            reset_battle_state()  # Use the new reset function
            return True
        return False
    except Exception as e:
        st.error(f"Error leaving room: {str(e)}")
        return False 
    
#lagibaru
def initialize_quiz():
    """Initialize session state variables if they don't exist"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
    if 'student_name' not in st.session_state:
        st.session_state.student_name = ""
    if 'questions' not in st.session_state:
        st.session_state.questions = []
    if 'shuffled_questions' not in st.session_state:
        st.session_state.shuffled_questions = []
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {}
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = "All Categories"
    if 'score_saved' not in st.session_state:
        st.session_state.score_saved = False



def shuffle_questions():
    if st.session_state.questions:
        shuffled = st.session_state.questions.copy()
        random.shuffle(shuffled)
        for q in shuffled:
            random.shuffle(q['options'])
        st.session_state.shuffled_questions = shuffled
        st.session_state.user_answers = {}
        st.session_state.submitted = False


def get_categories():
    try:
        response = supabase.table('questions').select('category').execute()
        categories = set(row['category'] for row in response.data)
        return ["All Categories"] + list(categories)
    except Exception as e:
        st.error(f"Error fetching categories: {str(e)}")
        return ["All Categories"]
    
#lagibaru
from datetime import datetime, timedelta

def save_performance(student_name, score, total_questions, category):
    """Save performance while preventing duplicate submissions."""
    try:
        # Check if student already submitted for this category in the last minute
        one_minute_ago = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
        
        recent_attempt = supabase.table('performance').select('*')\
            .eq('student_name', student_name)\
            .eq('category', category)\
            .gt('created_at', one_minute_ago)\
            .execute()
            
        if recent_attempt.data:
            # If there's a recent submission, don't save and show a message
            st.warning("Your score was already submitted! Please wait a moment before trying again.")
            return False
            
        # If no recent submission, save the new score
        data = {
            'student_name': student_name,
            'score': score,
            'total_questions': total_questions,
            'category': category,
            'created_at': datetime.utcnow().isoformat()
        }
        supabase.table('performance').insert(data).execute()
        
        st.success("Score saved successfully!")
        return True
        
    except Exception as e:
        st.error(f"Error saving performance: {str(e)}")
        return False
    


def get_performance_stats():
    try:
        response = supabase.table('performance').select('*').execute()
        if response.data:
            attempts = len(response.data)
            avg_score = sum(r['score'] * 100.0 / r['total_questions'] for r in response.data) / attempts
            max_score = max(r['score'] * 100.0 / r['total_questions'] for r in response.data)
            return attempts, avg_score, max_score
        return 0, 0, 0
    except Exception as e:
        st.error(f"Error getting performance stats: {str(e)}")
        return 0, 0, 0

def fetch_leaderboard():
    """Fetch top performers who have attempted 'All Categories' questions."""
    try:
        response = supabase.table('performance').select('*').execute()
        
        # Convert to DataFrame
        df = pd.DataFrame(response.data)
        
        if df.empty:
            return pd.DataFrame()
            
        # Create a copy instead of a view and filter for 'All Categories'
        df_filtered = df[df['category'] == 'All Categories'].copy()
        
        if df_filtered.empty:
            return pd.DataFrame()
        
        # Calculate percentage scores using loc
        df_filtered.loc[:, 'percentage'] = (df_filtered['score'] / df_filtered['total_questions'] * 100).round(2)
        
        # Group by student and get their best performance
        best_scores = df_filtered.groupby('student_name').agg({
            'score': 'max',
            'total_questions': 'first',
            'percentage': 'max'
        }).reset_index()
        
        # Sort by percentage and get top 10
        best_scores = best_scores.sort_values('percentage', ascending=False).head(10)
        
        return best_scores
        
    except Exception as e:
        st.error(f"Error fetching leaderboard: {str(e)}")
        return pd.DataFrame()
    
 
def display_leaderboard():
    """Display the leaderboard in a nice format."""
    leaderboard_data = fetch_leaderboard()
    
    if not leaderboard_data.empty:
        st.write("🏆 Top 10 All Categories Champions")
        st.info("These champions have successfully attempted questions in 'All Categories'!")
        
        # Style the leaderboard
        for i, row in leaderboard_data.iterrows():
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
                
                with col1:
                    # Display rank with medals for top 3
                    rank = i + 1
                    if rank == 1:
                        st.markdown("🥇")
                    elif rank == 2:
                        st.markdown("🥈")
                    elif rank == 3:
                        st.markdown("🥉")
                    else:
                        st.write(f"#{rank}")
                
                with col2:
                    st.write(f"**{row['student_name']}**")
                
                with col3:
                    st.write(f"{row['score']}/{row['total_questions']}")
                
                with col4:
                    # Color code the percentage
                    percentage = row['percentage']
                    if percentage >= 90:
                        st.success(f"{percentage}%")
                    elif percentage >= 70:
                        st.info(f"{percentage}%")
                    else:
                        st.warning(f"{percentage}%")
    else:
        st.info("No students have attempted the 'All Categories' quiz yet! 📚 Complete the 'All Categories' quiz to appear on the leaderboard.")


#Generate Room No
import random
import string
import uuid

def create_battle_room(selected_category):
    """Create a new battle room with questions and display code."""
    try:
        questions = get_all_questions(selected_category)
        shuffled_questions = random.sample(questions, min(len(questions), 5))
        
        formatted_questions = [{
            'question': q['question'],
            'options': q['options'],
            'answer': q['answer'],
            'explanation': q['explanation']
        } for q in shuffled_questions]
        
        # Generate a short display code
        display_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        battle_data = {
            'id': str(uuid.uuid4()),  # Keep UUID for database
            'display_code': display_code,  # Add display code
            'creator': st.session_state.student_name,
            'status': 'waiting',
            'created_at': datetime.utcnow().isoformat(),
            'questions': formatted_questions,
            'creator_score': 0,
            'joiner_score': 0,
            'category': selected_category
        }
        
        response = supabase.table('battle_rooms').insert(battle_data).execute()
        st.session_state.battle_questions = formatted_questions
        st.session_state.battle_id = response.data[0]['id']  # Store actual UUID
        return display_code  # Return display code for UI
        
    except Exception as e:
        st.error(f"Error creating battle room: {str(e)}")
        return None



def generate_room_code():
    """Generate a short, readable room code."""
    # Generate a 6-character code using numbers and uppercase letters
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))


#lagi baru
def initialize_battle_state():
    """Initialize all battle-related session state variables."""
    if 'battle_mode' not in st.session_state:
        st.session_state.battle_mode = False
    if 'battle_id' not in st.session_state:
        st.session_state.battle_id = None
    if 'battle_status' not in st.session_state:
        st.session_state.battle_status = None
    if 'battle_questions' not in st.session_state:
        st.session_state.battle_questions = []
    if 'battle_answers' not in st.session_state:
        st.session_state.battle_answers = {}
    if 'battle_submitted' not in st.session_state:
        st.session_state.battle_submitted = False
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0
    if 'battle_timer' not in st.session_state:
        st.session_state.battle_timer = 30  # 30 seconds per question
    if 'streak_bonus' not in st.session_state:
        st.session_state.streak_bonus = 0
    if 'total_battle_score' not in st.session_state:
        st.session_state.total_battle_score = 0
    if 'current_question_score' not in st.session_state:
        st.session_state.current_question_score = 0

#lagi baru
def calculate_question_score(remaining_time, streak):
    """Calculate score for a single question"""
    base_score = 1  # Base point for correct answer
    time_bonus = max(1, remaining_time // 5)  # Time bonus
    streak_multiplier = max(1, streak)  # Streak multiplier
    
    total = (base_score + time_bonus) * streak_multiplier
    return total

#lagi baru
def display_battle_quiz():
    """Display enhanced quiz for battle mode."""
    if not st.session_state.battle_questions:
        st.warning("No questions available.")
        return 0
    
    current_q_idx = st.session_state.current_question_index
    
    # Check if all questions are completed
    if current_q_idx >= len(st.session_state.battle_questions):
        battle_info = check_battle_status(st.session_state.battle_id)
        if battle_info:
            show_battle_results(battle_info)
        return st.session_state.total_battle_score


    q = st.session_state.battle_questions[current_q_idx]
    
    # Battle Stats Display
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Question", f"{current_q_idx + 1}/5")
    with col2:
        st.metric("Time Left", f"{st.session_state.battle_timer}s ⏱️")
    with col3:
        st.metric("Streak", f"{st.session_state.streak_bonus}x 🔥")
    with col4:
        st.metric("Score", st.session_state.total_battle_score)
    
    # Question Display
    st.subheader(f"Question {current_q_idx + 1}")
    st.markdown(f"**{q['question']}**")
    
    # Timer and Answer Check
    if st.session_state.battle_timer > 0:
        answer = st.radio(
            "Select your answer:",
            q['options'],
            key=f"battle_q_{current_q_idx}",
            index=None
        )
        
        if answer:
            is_correct = answer.strip() == q['answer'].strip()
            if is_correct:
                question_score = calculate_question_score(
                    st.session_state.battle_timer,
                    st.session_state.streak_bonus
                )
                st.session_state.streak_bonus += 1
                st.session_state.total_battle_score += question_score
                st.success(f"""✅ Correct! 
                Points breakdown:
                - Base score: 1
                - Time bonus: {max(1, st.session_state.battle_timer // 5)}
                - Streak multiplier: {max(1, st.session_state.streak_bonus - 1)}x
                Total for this question: {question_score} points!
                """)
            else:
                st.error("❌ Incorrect")
                st.info(f"Explanation: {q['explanation']}")
                st.session_state.streak_bonus = 0
                question_score = 0
            
            st.session_state.battle_answers[current_q_idx] = answer
            st.session_state.current_question_index += 1
            st.session_state.battle_timer = 30  # Reset timer
            st.session_state.current_question_score = question_score
            st.rerun()
            return question_score
    else:
        st.warning("⏰ Time's up!")
        st.session_state.current_question_index += 1
        st.session_state.battle_timer = 30
        st.session_state.streak_bonus = 0  # Reset streak on timeout
        st.rerun()
        return 0
    
    return 0

#lagi baru
def show_battle_results(battle_info):
    """Show final battle results with clear score comparison."""
    #st.divider()
    st.markdown("## 🏆 Battle Results")
    
    # Get player roles and scores
    is_creator = st.session_state.student_name == battle_info['creator']
    your_score = battle_info['creator_score'] if is_creator else battle_info['joiner_score']
    opponent_name = battle_info['joiner'] if is_creator else battle_info['creator']
    opponent_score = battle_info['joiner_score'] if is_creator else battle_info['creator_score']
    
    # Create a visual score comparison
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        st.markdown("### You")
        st.markdown(f"""
        <div style='padding: 20px; background-color: #f0f8ff; border-radius: 10px; text-align: center;'>
            <h2 style='margin: 0;'>{your_score} points</h2>
            <p style='margin: 5px 0;'>{st.session_state.student_name}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### VS")
        if your_score > opponent_score:
            st.markdown("### 🏆")
        elif your_score < opponent_score:
            st.markdown("### 😔")
        else:
            st.markdown("### 🤝")
    
    with col3:
        st.markdown("### Opponent")
        st.markdown(f"""
        <div style='padding: 20px; background-color: #fff0f0; border-radius: 10px; text-align: center;'>
            <h2 style='margin: 0;'>{opponent_score} points</h2>
            <p style='margin: 5px 0;'>{opponent_name}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Show result message
    st.divider()
    if your_score > opponent_score:
        st.success("🎉 Victory! You won the battle!")
        st.balloons()
    elif your_score < opponent_score:
        st.error("😔 Defeat! Your opponent won this time!")
    else:
        st.info("🤝 It's a tie! Well played both!")
    
    # Show action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Battle", type="primary"):
            reset_battle_state()
            st.rerun()
    with col2:
        if st.button("👋 Leave Battle"):
            leave_battle_room(battle_info['id'], is_creator)
            reset_battle_state()
            st.rerun()

#lagi baru
def display_live_scores(battle_info):
    """Display live scores for both players with visual indicators."""
    st.markdown("### 📊 Live Battle Scores")
    
    col1, col2 = st.columns(2)
    
    # Determine which player is which
    is_creator = st.session_state.student_name == battle_info['creator']
    your_score = battle_info['creator_score'] if is_creator else battle_info['joiner_score']
    opponent_name = battle_info['joiner'] if is_creator else battle_info['creator']
    opponent_score = battle_info['joiner_score'] if is_creator else battle_info['creator_score']
    
    # Your score card
    with col1:
        st.markdown("#### 🎯 Your Score")
        score_container = st.container()
        with score_container:
            st.markdown(f"""
            <div style='padding: 10px; border: 2px solid #4CAF50; border-radius: 5px; text-align: center;'>
                <h2 style='color: #4CAF50; margin: 0;'>{your_score}</h2>
                <p style='margin: 5px 0;'>Streak: {st.session_state.streak_bonus}x 🔥</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Opponent's score card
    with col2:
        st.markdown(f"#### 🤺 {opponent_name}'s Score")
        score_container = st.container()
        with score_container:
            st.markdown(f"""
            <div style='padding: 10px; border: 2px solid #2196F3; border-radius: 5px; text-align: center;'>
                <h2 style='color: #2196F3; margin: 0;'>{opponent_score}</h2>
            </div>
            """, unsafe_allow_html=True)
    
    

#lagibaru
def display_battle_tab():
    """Display enhanced battle mode interface."""
    if not st.session_state.student_name:
        st.info("Please enter your name in the sidebar to start battling!")
        return
        
    if not st.session_state.battle_mode:
           
        # Create or Join Battle
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("🎯 Create New Battle:")
            categories = get_categories()
            selected_category = st.selectbox(
                "Choose category:",
                categories,
                key="battle_category_select"
            )
            
            if st.button("Create Battle Room", type="primary"):
                display_code = create_battle_room(selected_category)
                if display_code:
                    st.session_state.battle_mode = True
                    st.session_state.battle_status = 'waiting'
                    st.session_state.current_question_index = 0
                    st.rerun()
        
        with col2:
            st.write("🤝 Join Battle:")
            room_code = st.text_input("Enter Room Code:")
            if room_code and st.button("Join Battle", type="secondary"):
                if join_battle_room(room_code):
                    st.session_state.battle_mode = True
                    st.session_state.battle_status = 'joined'
                    st.session_state.current_question_index = 0
                    st.rerun()
        
        # Show active battles
        st.divider()
        st.subheader("🎮 Active Battles")
        show_active_battles()
    
    else:
        # Active Battle Interface
        battle_info = check_battle_status(st.session_state.battle_id)
        if battle_info:
            # Battle Header
            st.title("⚔️ Live Battle")
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.code(f"Room Code: {battle_info['display_code']}")  # Show display code
            with col2:
                st.write(f"Category: **{battle_info['category']}**")
                                        
            if battle_info['status'] == 'waiting':
                st.info("👥 Waiting for opponent...")
                st.write("Share your room code to start the battle!")
                
                # Practice while waiting
                st.divider()
                display_battle_quiz()
                
            elif battle_info['status'] == 'in_progress':
                # Show Live Scores
                col1, col2 = st.columns(2)
                with col1:
                    your_score = battle_info['creator_score'] if st.session_state.student_name == battle_info['creator'] else battle_info['joiner_score']
                    st.metric("Your Score", your_score)
                with col2:
                    opponent = battle_info['joiner'] if st.session_state.student_name == battle_info['creator'] else battle_info['creator']
                    opponent_score = battle_info['joiner_score'] if st.session_state.student_name == battle_info['creator'] else battle_info['creator_score']
                    st.metric(f"{opponent}'s Score", opponent_score)
                
                # Show Battle Quiz
                st.divider()
                current_score = display_battle_quiz()
                
                # Update scores in database
                if current_score > 0:
                    is_creator = st.session_state.student_name == battle_info['creator']
                    update_battle_score(st.session_state.battle_id, is_creator, current_score)
                    st.rerun()
            
    

#baru


def show_active_battles():
    """Display list of active battle rooms."""
    try:
        # Get all rooms with 'waiting' status
        response = supabase.table('battle_rooms').select('*').eq('status', 'waiting').execute()
        
        if response.data:
            # Create a container for consistent styling
            with st.container():
                # Header for the battles list
                st.write("Available Battles:")
                
                # Display each active battle room
                for room in response.data:
                    # Skip if the room was created by the current user
                    if room['creator'] == st.session_state.student_name:
                        continue
                        
                    # Create a card-like container for each battle
                    with st.container():
                        # Use columns for layout
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                        
                        with col1:
                            st.write(f"🎮 Host: **{room['creator']}**")
                        
                        with col2:
                            st.write(f"📚 Category: {room['category']}")
                            
                        with col3:
                            # Format the creation time
                            created_at = datetime.fromisoformat(room['created_at'].replace('Z', '+00:00'))
                            time_ago = datetime.utcnow() - created_at
                            minutes_ago = int(time_ago.total_seconds() / 60)
                            
                            if minutes_ago < 1:
                                time_str = "Just now"
                            elif minutes_ago == 1:
                                time_str = "1 minute ago"
                            else:
                                time_str = f"{minutes_ago} minutes ago"
                                
                            st.write(f"⏰ Created: {time_str}")
                        
                        with col4:
                            # Join button with unique key for each room
                            if st.button("Join", key=f"join_{room['id']}", type="primary"):
                                if join_battle_room(room['id']):
                                    st.session_state.battle_mode = True
                                    st.session_state.battle_id = room['id']
                                    st.rerun()
                        
                        # Add a subtle divider between battles
                        st.markdown("---")
        else:
            # Show message when no battles are available
            st.info("No active battles found. Create one to start! 🎮")
            
    except Exception as e:
        st.error(f"Error loading active battles: {str(e)}")
        # Log the error for debugging
        print(f"Error in show_active_battles: {str(e)}")


#lama
def calculate_final_score():
    """Calculate final score including bonuses."""
    base_score = sum(1 for i, q in enumerate(st.session_state.battle_questions) 
                    if st.session_state.battle_answers.get(i) == q['answer'])
    
    streak_multiplier = max(1, st.session_state.streak_bonus)
    final_score = base_score * streak_multiplier
    
    return final_score




def get_player_battle_stats(player_name):
    """Get battle statistics for a player."""
    try:
        response = supabase.table('battle_rooms').select('*').or_(
            f"creator.eq.{player_name},joiner.eq.{player_name}"
        ).execute()
        
        stats = {
            'wins': 0,
            'max_streak': 0,
            'total_score': 0
        }
        
        for battle in response.data:
            if battle['status'] == 'completed':
                is_creator = battle['creator'] == player_name
                player_score = battle['creator_score'] if is_creator else battle['joiner_score']
                opponent_score = battle['joiner_score'] if is_creator else battle['creator_score']
                
                if player_score > opponent_score:
                    stats['wins'] += 1
                
                stats['total_score'] += player_score
                stats['max_streak'] = max(stats['max_streak'], 
                                        battle['streak_bonus']['creator' if is_creator else 'joiner'])
        
        return stats
        
    except Exception as e:
        st.error(f"Error fetching player stats: {str(e)}")
        return {'wins': 0, 'max_streak': 0, 'total_score': 0}



def reset_battle_state():
    """Reset all battle-related session state variables."""
    st.session_state.battle_mode = False
    st.session_state.battle_id = None
    st.session_state.battle_status = None
    st.session_state.battle_questions = []
    st.session_state.battle_answers = {}
    st.session_state.battle_submitted = False
    st.session_state.battle_category = None
    st.session_state.creating_battle = False


def display_admin_dashboard():
    st.title("👨‍💼 Admin Dashboard")
    
    # Statistics cards in a row
    col1, col2, col3, col4 = st.columns(4)
    
    question_count = get_question_count()
    attempts, avg_score, max_score = get_performance_stats()
    
    with col1:
        st.metric("Total Questions", question_count)
    with col2:
        st.metric("Total Attempts", attempts)
    with col3:
        st.metric("Average Score", f"{avg_score:.1f}%")
    with col4:
        st.metric("Highest Score", f"{max_score:.1f}%")
    
    # Upload section
    st.divider()
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload questions (CSV)", type=["csv"])
    with col2:
        category = st.text_input("Category", "General")
        if uploaded_file and st.button("Add Questions"):
            added_count = add_questions_from_csv(uploaded_file, category)
            if added_count > 0:
                st.success(f"Added {added_count} questions!")
                st.rerun()
    
    # Database Management Section
    st.divider()
    st.subheader("🗑️ Database Management")
    
    with st.expander("Delete All Records"):
        st.warning("⚠️ Warning: This action cannot be undone!")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            delete_questions = st.checkbox("Delete Questions")
        with col2:
            delete_battles = st.checkbox("Delete Battle Records")
            
        confirm_text = st.text_input("Type 'DELETE' to confirm:")
        if st.button("Delete Selected Records", type="primary"):
            if confirm_text == "DELETE":
                try:
                    if delete_questions:
                        supabase.table('questions').delete().gte('id', 0).execute()
                        st.success("Questions deleted!")
                                      
                    if delete_battles:
                        supabase.table('battle_rooms').delete().gte('id', '00000000-0000-0000-0000-000000000000').execute()
                        st.success("Battle records deleted!")
                        
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting records: {str(e)}")
            else:
                st.error("Please type 'DELETE' to confirm")

 
                       
    # Practice Summary and History tabs
    st.divider()
    tab1, tab2 = st.tabs(["Practice Summary", "Practice History"])
    
    with tab1:
        display_practice_summary()
    
    with tab2:
        display_practice_history()

def handle_answer_validation(user_answer, correct_answer):
    """Universal answer validation for both quiz and battle mode."""
    # Normalize both answers for comparison
    user_ans = str(user_answer).strip() if user_answer else ""
    correct_ans = str(correct_answer).strip() if correct_answer else ""
    return user_ans == correct_ans 


def initialize_battle_quiz_state():
    """Initialize battle quiz specific state"""
    if 'battle_questions' not in st.session_state:
        st.session_state.battle_questions = []
    if 'battle_answers' not in st.session_state:
        st.session_state.battle_answers = {}
    if 'battle_submitted' not in st.session_state:
        st.session_state.battle_submitted = False
    if 'battle_category' not in st.session_state:
        st.session_state.battle_category = "All Categories"



def handle_battle_question_submission(current_question, user_answer, question_index):
    """Handle battle question submission with proper answer validation."""
    if not user_answer:
        return False
        
    if user_answer == current_question['answer']:
        st.success("✅ Correct!")
        st.session_state.battle_answers[question_index] = user_answer
        return True
    else:
        st.error("❌ Incorrect")
        st.session_state.battle_answers[question_index] = user_answer
        return False
 
#lagibaru
def join_battle_room(display_code):
    """Join an existing battle room using display code."""
    try:
        # First find the room with this display code
        room = supabase.table('battle_rooms').select('*').eq('display_code', display_code).eq('status', 'waiting').execute()
        
        if not room.data:
            st.error("Room not found or already full")
            return False
        
        room_data = room.data[0]
        st.session_state.battle_questions = room_data['questions']
        st.session_state.battle_category = room_data['category']
        st.session_state.battle_id = room_data['id']  # Store actual UUID
            
        response = supabase.table('battle_rooms').update({
            'joiner': st.session_state.student_name,
            'status': 'in_progress',
            'joined_at': datetime.utcnow().isoformat()
        }).eq('id', room_data['id']).execute()
        
        if response.data:
            return True
        return False
    except Exception as e:
        st.error(f"Error joining battle room: {str(e)}")
        return False

  
def update_battle_score(room_id, is_creator, score):
    """Update the score in battle room."""
    try:
        field = 'creator_score' if is_creator else 'joiner_score'
        supabase.table('battle_rooms').update({
            field: score,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', room_id).execute()
    except Exception as e:
        st.error(f"Error updating score: {str(e)}")


def check_battle_status(room_id):
    """Check the status of the battle room with better error handling."""
    if not room_id:
        return None
        
    try:
        response = supabase.table('battle_rooms').select('*').eq('id', room_id).execute()
        if not response.data:
            st.error("Battle room not found. It may have been deleted.")
            # Reset battle mode if room doesn't exist
            st.session_state.battle_mode = False
            st.session_state.battle_id = None
            return None
        return response.data[0]
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None

def leave_battle_room(room_id, is_creator):
    """Handle leaving the battle room."""
    try:
        # Update room status and mark who left
        data = {
            'status': 'completed',
            'left_by': 'creator' if is_creator else 'joiner'
        }
        supabase.table('battle_rooms').update(data).eq('id', room_id).execute()
        return True
    except Exception as e:
        st.error(f"Error leaving room: {str(e)}")
        return False

def sign_out():
    """Reset all user-related session state variables."""
    # Clear all user states
    for key in list(st.session_state.keys()):
        # Keep admin login state if logged in
        if key != "password_correct":
            del st.session_state[key]
    # Reinitialize necessary states
    initialize_quiz()
    initialize_battle_state()


import streamlit as st

def show_user_feedback_page():

    # HTML content with a styled box
    content = """
    <div style="border: 2px solid #008080; padding: 20px; background-color: #e0f7fa; font-size: 18px; color: #333;">
     <strong>We appreciate your input!</strong>
        <ol>
            <li>Kindly submit your feedback using this Google Form <a href="https://forms.gle/mosheKchXNgUqa9M9" target="_blank">User Feedback</a>.</li>
            <li>If you experience any issues or need assistance, please reach out to us at: <a href="mailto:ainie_hayati@psis.edu.my">ainie_hayati@psis.edu.my</a>.</li>
        </ol>
    </div>
    """

    # Render HTML content in Streamlit 
    st.markdown(content, unsafe_allow_html=True)

        
def admin_logout():
    """Handle admin logout."""
   
    if st.session_state.get("password_correct"):
        if st.sidebar.button("Logout"):
            st.session_state["password_correct"] = False
            st.rerun()


if __name__ == "__main__":
    main()




