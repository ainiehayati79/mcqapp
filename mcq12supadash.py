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

    if "password_correct" not in st.session_state:
        st.sidebar.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.sidebar.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.sidebar.error("😕 Password incorrect")
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

def display_quiz():
    # Student quiz interface
    st.title("📚 MCQ Quiz System")
    
    # Student name input (only show if not already set)
    if not st.session_state.student_name:
        st.subheader("Welcome to the Quiz!")
        name_input = st.text_input("Please enter your name to begin:", key="name_input")
        if name_input:
            st.session_state.student_name = name_input
            st.rerun()
        return
    
    # Show student name
    st.subheader(f"Student: {st.session_state.student_name}")
    
    # Category selection
    categories = get_categories()
    selected_category = st.selectbox(
        "Select Category:",
        categories,
        key="category_select"
    )
    
    # Load questions if category changed or not loaded
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
        
        key = f"q_{i}"
        if not st.session_state.submitted:
            user_answer = st.radio(
                "Select your answer:",
                q['options'],
                key=key,
                index=None
            )
            st.session_state.user_answers[i] = user_answer
        else:
            user_answer = st.session_state.user_answers.get(i)
            st.radio(
                "Your answer:",
                q['options'],
                key=key,
                index=q['options'].index(user_answer) if user_answer else None,
                disabled=True
            )
    
    # Submit/Restart buttons
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 New Quiz"):
            st.session_state.questions = []
            st.session_state.submitted = False
            st.session_state.user_answers = {}
            st.rerun()
    
    if not st.session_state.submitted:
        with col2:
            if st.button("📤 Submit Answers"):
                if all(st.session_state.user_answers.values()):
                    st.session_state.submitted = True
                    st.rerun()
                else:
                    st.error("Please answer all questions before submitting.")
    
    # Show results
    if st.session_state.submitted:
        st.divider()
        st.subheader("📊 Results")
        
        score = 0
        for i, q in enumerate(st.session_state.shuffled_questions):
            user_ans = st.session_state.user_answers.get(i, "No answer")
            correct_ans = q['answer']
            
            with st.expander(f"Question {i+1}", expanded=False):
                if user_ans == correct_ans:
                    st.success(f"✅ Correct! ({correct_ans})")
                    score += 1
                else:
                    st.error(f"❌ Incorrect. Your answer: {user_ans} | Correct: {correct_ans}")
                st.markdown(f"*Explanation*: {q['explanation']}")
        
        st.success(f"**Final Score: {score}/{len(st.session_state.questions)}**")
        
        # Save performance
        save_performance(
            st.session_state.student_name,
            score,
            len(st.session_state.questions),
            selected_category
        )
        
        if score == len(st.session_state.questions):
            st.balloons()

def main():
    # Initialize session state
    initialize_quiz()
    initialize_battle_state()
    
    # Add tabs for Quiz and Admin Dashboard
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Quiz", "📊 Admin Dashboard", "🥇Leader Board", "⚔️ Live Battle"])
    
    with tab1:
        display_quiz()
    
    with tab2:
        # Sidebar admin section (login)
        st.sidebar.title("👨‍💼 Admin Panel")
        
        # Check if admin is logged in
        is_admin = check_password()
        
        if is_admin:
            st.sidebar.success("Welcome, Admin! 🔓")
            # Show admin dashboard in this tab
            display_admin_dashboard()
            # Add logout button to sidebar
            admin_logout()
        else:
            st.title("Admin Dashboard")
            st.info("Please log in as admin to view the dashboard.")

    with tab3:
       display_leaderboard()
    
    with tab4:
         # Battle mode
        if st.session_state.student_name:
            display_battle_mode()
        else:
            st.info("Please enter your name in the Quiz tab first!")
  

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

def save_performance(student_name, score, total_questions, category):
    try:
        data = {
            'student_name': student_name,
            'score': score,
            'total_questions': total_questions,
            'category': category
        }
        supabase.table('performance').insert(data).execute()
    except Exception as e:
        st.error(f"Error saving performance: {str(e)}")

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
    """Fetch top performers from the database."""
    try:
        response = supabase.table('performance').select('*').execute()
        
        # Convert to DataFrame for easier manipulation
        import pandas as pd
        df = pd.DataFrame(response.data)
        
        # Calculate percentage scores
        df['percentage'] = (df['score'] / df['total_questions'] * 100).round(2)
        
        # Group by student and get their best performance
        best_scores = df.groupby('student_name').agg({
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
    st.subheader("🏆 Leaderboard")
    
    leaderboard_data = fetch_leaderboard()
    
    if not leaderboard_data.empty:
        # Create three columns for different metrics
        st.write("Top 10 Performers")
        
        # Style the leaderboard
        for i, row in leaderboard_data.iterrows():
            # Create a card-like display for each entry
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
        st.info("No quiz attempts yet!")

"""Battle Mode"""
def initialize_battle_state():
    """Initialize battle-related session state variables."""
    if 'battle_mode' not in st.session_state:
        st.session_state.battle_mode = False
    if 'battle_id' not in st.session_state:
        st.session_state.battle_id = None
    if 'opponent_name' not in st.session_state:
        st.session_state.opponent_name = None
    if 'battle_status' not in st.session_state:
        st.session_state.battle_status = None

def create_battle_room():
    """Create a new battle room and return the room code."""
    try:
        battle_data = {
            'creator': st.session_state.student_name,
            'status': 'waiting',
            'created_at': datetime.utcnow().isoformat(),  # Using utcnow() for consistency
            'questions': [q['question'] for q in st.session_state.questions],
            'creator_score': 0,
            'joiner_score': 0
        }
        response = supabase.table('battle_rooms').insert(battle_data).execute()
        return response.data[0]['id']
    except Exception as e:
        st.error(f"Error creating battle room: {str(e)}")
        return None

def join_battle_room(room_code):
    """Join an existing battle room."""
    try:
        # First check if room exists and is available
        room = supabase.table('battle_rooms').select('*').eq('id', room_code).eq('status', 'waiting').execute()
        
        if not room.data:
            st.error("Room not found or already full")
            return False
            
        response = supabase.table('battle_rooms').update({
            'joiner': st.session_state.student_name,
            'status': 'in_progress',
            'joined_at': datetime.utcnow().isoformat()
        }).eq('id', room_code).execute()
        
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
 

def display_battle_mode():
    """Display the battle mode interface with improved error handling."""
    st.subheader("⚔️ Battle Mode")
    
    # Add a refresh button
    if st.session_state.get('battle_mode'):
        if st.button("🔄 Refresh Status"):
            st.rerun()
    
    if not st.session_state.get('battle_mode', False):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Create Battle Room"):
                room_id = create_battle_room()
                if room_id:
                    st.session_state.battle_mode = True
                    st.session_state.battle_id = room_id
                    st.session_state.battle_status = 'waiting'
                    st.rerun()
        
        with col2:
            room_code = st.text_input("Enter Room Code to Join:")
            if room_code and st.button("Join Battle"):
                if join_battle_room(room_code):
                    st.session_state.battle_mode = True
                    st.session_state.battle_id = room_code
                    st.session_state.battle_status = 'joined'
                    st.rerun()
    
    else:
        # Display battle room status
        battle_info = check_battle_status(st.session_state.battle_id)
        
        if battle_info:
            st.write(f"Room Code: **{st.session_state.battle_id}**")
            
            # Add leave battle button
            if st.button("❌ Leave Battle"):
                st.session_state.battle_mode = False
                st.session_state.battle_id = None
                st.session_state.battle_status = None
                st.rerun()
            
            if battle_info['status'] == 'waiting':
                st.info("👥 Waiting for opponent to join...")
                st.write("Share this room code with your opponent!")
                
            elif battle_info['status'] == 'in_progress':
                # Display live scores
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Your Score", 
                        battle_info['creator_score'] if st.session_state.student_name == battle_info['creator'] else battle_info['joiner_score']
                    )
                with col2:
                    opponent_name = battle_info['joiner'] if st.session_state.student_name == battle_info['creator'] else battle_info['creator']
                    st.metric(
                        f"{opponent_name}'s Score", 
                        battle_info['joiner_score'] if st.session_state.student_name == battle_info['creator'] else battle_info['creator_score']
                    )
                
                # Display the quiz
                display_quiz()
                
                # Update scores after each answer
                if st.session_state.answer_submitted:
                    is_creator = st.session_state.student_name == battle_info['creator']
                    current_score = sum(1 for i, q in enumerate(st.session_state.questions) 
                                     if st.session_state.user_answers.get(i) == q['answer'])
                    update_battle_score(st.session_state.battle_id, is_creator, current_score)
            
            elif battle_info['status'] == 'completed':
                st.success("🎮 Battle Complete!")
                
                # Show winner
                if battle_info['creator_score'] > battle_info['joiner_score']:
                    st.balloons()
                    st.success(f"🏆 Winner: {battle_info['creator']}")
                elif battle_info['creator_score'] < battle_info['joiner_score']:
                    st.balloons()
                    st.success(f"🏆 Winner: {battle_info['joiner']}")
                else:
                    st.info("🤝 It's a tie!")
                
                # Option to start new battle
                if st.button("🔄 Start New Battle"):
                    st.session_state.battle_mode = False
                    st.session_state.battle_id = None
                    st.session_state.battle_status = None
                    st.rerun()
        else:
            # Room not found or error occurred
            st.error("Battle room not available. Please create a new room or join an existing one.")
            st.session_state.battle_mode = False
            st.session_state.battle_id = None
            st.rerun()


def admin_logout():
    """Handle admin logout."""
    if st.session_state.get("password_correct"):
        if st.sidebar.button("Logout"):
            st.session_state["password_correct"] = False
            st.rerun()


if __name__ == "__main__":
    main()


