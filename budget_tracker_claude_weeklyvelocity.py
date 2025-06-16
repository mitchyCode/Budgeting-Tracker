import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import json

st.set_page_config(page_title="Personal Budget Tracker", page_icon="💰", layout="wide")

# Initialize session state for data persistence
def initialize_session_state():
    if 'user_setup_complete' not in st.session_state:
        st.session_state.user_setup_complete = False
    if 'user_data' not in st.session_state:
        st.session_state.user_data = {}
    if 'expenses' not in st.session_state:
        st.session_state.expenses = []
    if 'savings_goals' not in st.session_state:
        st.session_state.savings_goals = []
    if 'last_updated' not in st.session_state:
        st.session_state.last_updated = datetime.now().date()
    if 'current_month_year' not in st.session_state:
        today = datetime.now()
        st.session_state.current_month_year = f"{today.year}-{today.month:02d}"
    if 'last_reset_check' not in st.session_state:
        st.session_state.last_reset_check = datetime.now().date()

def save_user_data():
    """Save user data to session state (in a real app, this would save to a database)"""
    pass

def load_user_data():
    """Load user data from storage (in a real app, this would load from a database)"""
    pass

def calculate_next_payment_date(frequency, payment_day):
    """Calculate when the next payment should occur"""
    today = date.today()
    
    if frequency == "Monthly":
        if today.day <= payment_day:
            next_payment = today.replace(day=payment_day)
        else:
            if today.month == 12:
                next_payment = date(today.year + 1, 1, payment_day)
            else:
                try:
                    next_payment = today.replace(month=today.month + 1, day=payment_day)
                except ValueError:
                    next_payment = today.replace(month=today.month + 1, day=28)
        return next_payment
    
    elif frequency == "Weekly":
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        target_weekday = days_of_week.index(payment_day)
        days_ahead = target_weekday - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    elif frequency == "Fortnightly":
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        target_weekday = days_of_week.index(payment_day)
        days_ahead = target_weekday - today.weekday()
        if days_ahead <= 0:
            days_ahead += 14
        else:
            days_ahead += 7
        return today + timedelta(days=days_ahead)

def check_monthly_reset():
    """Check if we need to reset for a new month based on user's reset day"""
    if not st.session_state.user_setup_complete:
        return
    
    user_data = st.session_state.user_data
    today = datetime.now()
    last_check = st.session_state.last_reset_check
    
    # Get user's preferred reset day (default to 1st of month)
    reset_day = user_data.get('monthly_reset_day', 1)
    
    # Calculate what the current month should be based on reset day
    if today.day >= reset_day:
        # We're past the reset day, so current month is this month
        current_month_year = f"{today.year}-{today.month:02d}"
    else:
        # We're before the reset day, so current month is last month
        if today.month == 1:
            current_month_year = f"{today.year - 1}-12"
        else:
            current_month_year = f"{today.year}-{today.month - 1:02d}"
    
    # Check if we need to advance to a new month
    if current_month_year != st.session_state.current_month_year:
        old_month = st.session_state.current_month_year
        st.session_state.current_month_year = current_month_year
        
        # Show month transition message
        old_date = datetime.strptime(old_month, "%Y-%m")
        new_date = datetime.strptime(current_month_year, "%Y-%m")
        
        st.success(f"📅 New budget month started! Tracking expenses for {new_date.strftime('%B %Y')}")
        st.info(f"Previous month ({old_date.strftime('%B %Y')}) data has been archived and is still accessible for analysis.")
    
    # Check for weekly reset (Monday)
    if today.weekday() == 0 and last_check.weekday() != 0:  # Today is Monday and last check wasn't Monday
        st.success("📅 New week started! Weekly budget tracking has reset for this week (Monday-Sunday).")
    
    st.session_state.last_reset_check = today.date()

def get_spending_velocity_data():
    """Calculate spending velocity for current week vs recent weeks"""
    if not st.session_state.expenses:
        return None
    
    today = datetime.now()
    current_weekday = today.weekday()  # 0 = Monday, 6 = Sunday
    
    # Get current week expenses (Monday to now)
    days_since_monday = today.weekday()
    current_week_start = today - timedelta(days=days_since_monday)
    current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get expenses for current week so far
    current_week_expenses = []
    for expense in st.session_state.expenses:
        if expense['amount'] > 0:  # Only count actual expenses, not income
            expense_date = datetime.strptime(expense['date'], "%Y-%m-%d %H:%M")
            if current_week_start <= expense_date <= today:
                current_week_expenses.append(expense)
    
    current_week_spending = sum(exp['amount'] for exp in current_week_expenses)
    
    # Get last 4 complete weeks for comparison
    past_weeks_spending = []
    for week_offset in range(1, 5):  # Last 4 weeks
        week_start = current_week_start - timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=current_weekday)  # Same day of week as today
        
        week_expenses = []
        for expense in st.session_state.expenses:
            if expense['amount'] > 0:
                expense_date = datetime.strptime(expense['date'], "%Y-%m-%d %H:%M")
                if week_start <= expense_date <= week_end:
                    week_expenses.append(expense)
        
        week_spending = sum(exp['amount'] for exp in week_expenses)
        if week_spending > 0:  # Only include weeks with spending
            past_weeks_spending.append(week_spending)
    
    if not past_weeks_spending:
        return None
    
    # Calculate average spending for same period in past weeks
    avg_past_spending = sum(past_weeks_spending) / len(past_weeks_spending)
    
    if avg_past_spending == 0:
        return None
    
    # Calculate velocity (percentage difference)
    velocity_percent = ((current_week_spending - avg_past_spending) / avg_past_spending) * 100
    
    return {
        'current_week_spending': current_week_spending,
        'avg_past_spending': avg_past_spending,
        'velocity_percent': velocity_percent,
        'weeks_compared': len(past_weeks_spending),
        'current_weekday': current_weekday
    }

def display_spending_velocity():
    """Display the spending velocity tracker"""
    velocity_data = get_spending_velocity_data()
    
    if not velocity_data:
        # Show placeholder when there's not enough data
        st.subheader("⚡ Weekly Spending Velocity")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("This Week", "$0.00")
        
        with col2:
            st.metric("Past Weeks Avg", "Not enough data")
        
        with col3:
            st.metric("Spending Pace", "➡️ Building data...")
        
        st.info("💡 **Getting started:** Add some expenses this week and last week to see your spending velocity! The tracker needs at least one week of historical data to compare against.")
        return
    
    current_spending = velocity_data['current_week_spending']
    avg_spending = velocity_data['avg_past_spending']
    velocity = velocity_data['velocity_percent']
    weeks_compared = velocity_data['weeks_compared']
    current_weekday = velocity_data['current_weekday']
    
    # Get day name for context
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    current_day = days[current_weekday]
    
    st.subheader("⚡ Weekly Spending Velocity")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            f"This Week (Mon-{current_day})",
            f"${current_spending:.2f}"
        )
    
    with col2:
        st.metric(
            f"Avg Past {weeks_compared} Weeks",
            f"${avg_spending:.2f}"
        )
    
    with col3:
        # Determine status and color
        if velocity <= -20:
            status = "Much Slower"
            delta_color = "normal"
            emoji = "🐌"
        elif velocity <= -5:
            status = "Slower"
            delta_color = "normal"
            emoji = "📉"
        elif velocity <= 5:
            status = "On Pace"
            delta_color = "off"
            emoji = "➡️"
        elif velocity <= 20:
            status = "Faster"
            delta_color = "inverse"
            emoji = "📈"
        else:
            status = "Much Faster"
            delta_color = "inverse"
            emoji = "🚀"
        
        st.metric(
            "Spending Pace",
            f"{emoji} {status}",
            f"{velocity:+.0f}%",
            delta_color=delta_color
        )
    
    # Add contextual message
    if velocity > 20:
        st.warning(f"💡 **Heads up!** You're spending much faster than usual. Consider reviewing your recent purchases.")
    elif velocity > 5:
        st.info(f"📊 **Notice:** Your spending is slightly above your normal pace.")
    elif velocity < -20:
        st.success(f"🎉 **Great job!** You're spending much less than usual this week.")
    elif velocity < -5:
        st.success(f"👍 **Nice!** You're spending below your normal pace.")
    else:
        st.info(f"✅ **On track:** Your spending pace is similar to recent weeks.")
    
    # Show breakdown by day of week if we have enough data
    if current_weekday >= 2:  # Wednesday or later
        with st.expander("📅 Daily Breakdown", expanded=False):
            st.write("**Spending by day this week:**")
            
            # Calculate daily spending for current week
            today = datetime.now()
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            
            daily_spending = {i: 0 for i in range(current_weekday + 1)}
            
            for expense in st.session_state.expenses:
                if expense['amount'] > 0:
                    expense_date = datetime.strptime(expense['date'], "%Y-%m-%d %H:%M")
                    if expense_date >= week_start.replace(hour=0, minute=0, second=0, microsecond=0):
                        day_of_week = expense_date.weekday()
                        if day_of_week <= current_weekday:
                            daily_spending[day_of_week] += expense['amount']
            
            for day_num in range(current_weekday + 1):
                day_name = days[day_num]
                amount = daily_spending[day_num]
                st.write(f"• **{day_name}:** ${amount:.2f}")

def get_category_trends():
    """Calculate spending trends for each category"""
    if len(st.session_state.expenses) < 2:
        return {}
    
    user_data = st.session_state.user_data
    trends = {}
    
    for category in user_data['categories']:
        frequency = user_data['category_frequencies'][category]
        
        if frequency == "Weekly":
            # Compare current week to average of last 4 weeks
            current_period_spending = get_category_spending_current_week(category)
            past_periods_spending = get_category_spending_past_weeks(category, 4)
        else:
            # Compare current month to average of last 3 months
            current_period_spending = get_category_spending_current_month(category)
            past_periods_spending = get_category_spending_past_months(category, 3)
        
        if not past_periods_spending or len(past_periods_spending) == 0:
            trends[category] = {
                'arrow': '➡️',
                'status': 'No data',
                'percent': 0
            }
            continue
        
        avg_past_spending = sum(past_periods_spending) / len(past_periods_spending)
        
        if avg_past_spending == 0:
            if current_period_spending > 0:
                trends[category] = {
                    'arrow': '⬆️',
                    'status': 'New spending',
                    'percent': 100
                }
            else:
                trends[category] = {
                    'arrow': '➡️',
                    'status': 'Stable',
                    'percent': 0
                }
            continue
        
        # Calculate percentage change
        percent_change = ((current_period_spending - avg_past_spending) / avg_past_spending) * 100
        
        # Determine arrow and status
        if percent_change >= 25:
            arrow = '⬆️⬆️'
            status = 'Much higher'
        elif percent_change >= 10:
            arrow = '⬆️'
            status = 'Higher'
        elif percent_change >= -10:
            arrow = '➡️'
            status = 'Stable'
        elif percent_change >= -25:
            arrow = '⬇️'
            status = 'Lower'
        else:
            arrow = '⬇️⬇️'
            status = 'Much lower'
        
        trends[category] = {
            'arrow': arrow,
            'status': status,
            'percent': percent_change
        }
    
    return trends

def get_category_spending_current_week(category):
    """Get spending for a category in the current week"""
    today = datetime.now()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    spending = 0
    for expense in st.session_state.expenses:
        if expense['amount'] > 0 and expense['category'] == category:
            expense_date = datetime.strptime(expense['date'], "%Y-%m-%d %H:%M")
            if week_start <= expense_date <= today:
                spending += expense['amount']
    
    return spending

def get_category_spending_past_weeks(category, num_weeks):
    """Get spending for a category in past N weeks"""
    today = datetime.now()
    days_since_monday = today.weekday()
    current_week_start = today - timedelta(days=days_since_monday)
    
    past_weeks = []
    for week_offset in range(1, num_weeks + 1):
        week_start = current_week_start - timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        week_spending = 0
        for expense in st.session_state.expenses:
            if expense['amount'] > 0 and expense['category'] == category:
                expense_date = datetime.strptime(expense['date'], "%Y-%m-%d %H:%M")
                if week_start <= expense_date <= week_end:
                    week_spending += expense['amount']
        
        past_weeks.append(week_spending)
    
    return [week for week in past_weeks if week > 0]  # Only return weeks with spending

def get_category_spending_current_month(category):
    """Get spending for a category in the current budget month"""
    current_month = st.session_state.current_month_year
    spending = 0
    
    for expense in st.session_state.expenses:
        if expense['amount'] > 0 and expense['category'] == category:
            expense_date = datetime.strptime(expense['date'], "%Y-%m-%d %H:%M")
            expense_month = f"{expense_date.year}-{expense_date.month:02d}"
            
            if expense_month == current_month:
                spending += expense['amount']
    
    return spending

def get_category_spending_past_months(category, num_months):
    """Get spending for a category in past N budget months"""
    current_month = st.session_state.current_month_year
    current_date = datetime.strptime(current_month, "%Y-%m")
    
    past_months = []
    for month_offset in range(1, num_months + 1):
        # Calculate past month
        if current_date.month - month_offset <= 0:
            past_month = current_date.replace(
                year=current_date.year - 1,
                month=12 + (current_date.month - month_offset)
            )
        else:
            past_month = current_date.replace(month=current_date.month - month_offset)
        
        past_month_str = f"{past_month.year}-{past_month.month:02d}"
        
        month_spending = 0
        for expense in st.session_state.expenses:
            if expense['amount'] > 0 and expense['category'] == category:
                expense_date = datetime.strptime(expense['date'], "%Y-%m-%d %H:%M")
                expense_month = f"{expense_date.year}-{expense_date.month:02d}"
                
                if expense_month == past_month_str:
                    month_spending += expense['amount']
        
        past_months.append(month_spending)
    
    return [month for month in past_months if month > 0]  # Only return months with spending

def get_current_week_expenses():
    """Get expenses for the current week (Monday to Sunday)"""
    today = datetime.now()
    
    # Calculate the start of this week (Monday)
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate the end of this week (Sunday)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    current_week_expenses = []
    
    for expense in st.session_state.expenses:
        expense_date = datetime.strptime(expense['date'], "%Y-%m-%d %H:%M")
        
        if week_start <= expense_date <= week_end:
            current_week_expenses.append(expense)
    
    return current_week_expenses

def get_current_month_expenses():
    """Get expenses for the current budget month"""
    current_month = st.session_state.current_month_year
    current_expenses = []
    
    for expense in st.session_state.expenses:
        expense_date = datetime.strptime(expense['date'], "%Y-%m-%d %H:%M")
        expense_month = f"{expense_date.year}-{expense_date.month:02d}"
        
        if expense_month == current_month:
            current_expenses.append(expense)
    
    return current_expenses

def get_expenses_by_month(month_year=None):
    """Get expenses for a specific month (format: YYYY-MM)"""
    if month_year is None:
        month_year = st.session_state.current_month_year
    
    month_expenses = []
    
    for expense in st.session_state.expenses:
        expense_date = datetime.strptime(expense['date'], "%Y-%m-%d %H:%M")
        expense_month = f"{expense_date.year}-{expense_date.month:02d}"
        
        if expense_month == month_year:
            month_expenses.append(expense)
    
    return month_expenses

def get_available_months():
    """Get list of all months that have expenses"""
    months = set()
    
    for expense in st.session_state.expenses:
        expense_date = datetime.strptime(expense['date'], "%Y-%m-%d %H:%M")
        month_year = f"{expense_date.year}-{expense_date.month:02d}"
        months.add(month_year)
    
    # Always include current month
    months.add(st.session_state.current_month_year)
    
    # Sort months (newest first)
    sorted_months = sorted(list(months), reverse=True)
    return sorted_months

def check_and_add_income():
    """Check if income should be added and handle it"""
    if not st.session_state.user_setup_complete:
        return
    
    user_data = st.session_state.user_data
    today = date.today()
    last_updated = st.session_state.last_updated
    
    next_payment_date = calculate_next_payment_date(
        user_data['income_frequency'], 
        user_data['payment_day']
    )
    
    if today >= next_payment_date and last_updated < today:
        income_to_add = user_data['income_amount']
        
        st.success(f"🎉 Payday! Your {user_data['income_frequency'].lower()} income of ${income_to_add:,.2f} has been added to your balance!")
        
        st.session_state.user_data['current_balance'] += income_to_add
        st.session_state.last_updated = today
        
        income_record = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'category': 'Income',
            'amount': -income_to_add,
            'description': f'{user_data["income_frequency"]} Income',
            'frequency': user_data['income_frequency']
        }
        st.session_state.expenses.append(income_record)

def update_income_section():
    """Allow users to update their income information"""
    st.header("💰 Update Income Information")
    
    user_data = st.session_state.user_data
    
    with st.form("update_income_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_income = st.number_input("New Income Amount ($):", 
                                       value=float(user_data['income_amount']), 
                                       min_value=0.0, step=0.01)
        with col2:
            new_frequency = st.selectbox("Income Frequency:", 
                                       ["Monthly", "Fortnightly", "Weekly"],
                                       index=["Monthly", "Fortnightly", "Weekly"].index(user_data['income_frequency']))
        
        if new_frequency == "Monthly":
            new_payment_day = st.selectbox("Payment Day of Month:", 
                                         list(range(1, 32)),
                                         index=user_data['payment_day'] - 1 if isinstance(user_data['payment_day'], int) else 0)
        else:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            current_day = user_data['payment_day'] if user_data['payment_day'] in days else "Monday"
            new_payment_day = st.selectbox("Payment Day of Week:", days, index=days.index(current_day))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Update Income", type="primary"):
                st.session_state.user_data['income_amount'] = new_income
                st.session_state.user_data['income_frequency'] = new_frequency
                st.session_state.user_data['payment_day'] = new_payment_day
                st.success("Income information updated successfully!")
                st.session_state.show_income_update = False
                st.rerun()
        
        with col2:
            if st.form_submit_button("Cancel"):
                st.session_state.show_income_update = False
                st.rerun()

def manage_categories_section():
    """Allow users to add, edit, or remove budget categories"""
    st.header("📋 Manage Budget Categories")
    
    user_data = st.session_state.user_data
    
    st.subheader("➕ Add New Category")
    with st.form("add_category_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_category = st.text_input("Category Name:")
        with col2:
            new_budget = st.number_input("Budget Amount ($):", min_value=0.0, step=0.01)
        with col3:
            new_frequency = st.selectbox("Frequency:", ["Monthly", "Weekly"])
        
        if st.form_submit_button("Add Category", type="primary"):
            if new_category.strip() and new_budget > 0:
                if new_category.strip() not in user_data['categories']:
                    st.session_state.user_data['categories'].append(new_category.strip())
                    st.session_state.user_data['category_budgets'][new_category.strip()] = new_budget
                    st.session_state.user_data['category_frequencies'][new_category.strip()] = new_frequency
                    st.success(f"Added {new_category.strip()}: ${new_budget:.2f} {new_frequency.lower()}")
                    st.rerun()
                else:
                    st.error("Category already exists!")
            else:
                st.error("Please enter both category name and budget amount.")
    
    st.subheader("✏️ Edit Existing Categories")
    
    categories_to_remove = []
    
    for cat in user_data['categories']:
        with st.expander(f"📝 {cat}"):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                new_name = st.text_input("Category Name:", value=cat, key=f"edit_name_{cat}")
            with col2:
                new_budget = st.number_input("Budget ($):", 
                                           value=float(user_data['category_budgets'][cat]),
                                           min_value=0.0, step=0.01, key=f"edit_budget_{cat}")
            with col3:
                current_freq = user_data['category_frequencies'][cat]
                new_freq = st.selectbox("Frequency:", ["Monthly", "Weekly"], 
                                      index=0 if current_freq == "Monthly" else 1,
                                      key=f"edit_freq_{cat}")
            with col4:
                st.write("")
                if st.button("💾 Update", key=f"update_{cat}"):
                    if new_name.strip() and new_budget > 0:
                        if new_name.strip() != cat:
                            categories_to_remove.append(cat)
                            st.session_state.user_data['categories'].append(new_name.strip())
                        
                        st.session_state.user_data['category_budgets'][new_name.strip()] = new_budget
                        st.session_state.user_data['category_frequencies'][new_name.strip()] = new_freq
                        st.success(f"Updated {new_name.strip()}")
                        st.rerun()
                
                if st.button("❌ Remove", key=f"remove_{cat}"):
                    categories_to_remove.append(cat)
                    st.rerun()
    
    for cat in categories_to_remove:
        if cat in st.session_state.user_data['categories']:
            st.session_state.user_data['categories'].remove(cat)
            del st.session_state.user_data['category_budgets'][cat]
            del st.session_state.user_data['category_frequencies'][cat]
    
    if st.button("✅ Done Managing Categories"):
        st.session_state.show_category_management = False
        st.rerun()

def manage_savings_goals():
    """Manage savings goals interface"""
    st.header("🎯 Savings Goals")
    
    st.subheader("➕ Add New Savings Goal")
    with st.form("add_savings_goal"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            goal_name = st.text_input("Goal Name:", placeholder="Emergency Fund, Vacation, etc.")
        with col2:
            target_amount = st.number_input("Target Amount ($):", min_value=0.0, step=50.0)
        with col3:
            current_amount = st.number_input("Current Amount ($):", min_value=0.0, step=10.0)
        
        goal_description = st.text_area("Description (optional):", placeholder="Why is this goal important to you?")
        
        if st.form_submit_button("Add Goal", type="primary"):
            if goal_name.strip() and target_amount > 0:
                new_goal = {
                    'id': len(st.session_state.savings_goals),
                    'name': goal_name.strip(),
                    'target_amount': target_amount,
                    'current_amount': current_amount,
                    'description': goal_description,
                    'created_date': datetime.now().isoformat(),
                    'completed': False
                }
                st.session_state.savings_goals.append(new_goal)
                st.success(f"Added savings goal: {goal_name}")
                st.rerun()
            else:
                st.error("Please enter a goal name and target amount.")
    
    if st.session_state.savings_goals:
        st.subheader("📈 Your Savings Goals")
        
        for i, goal in enumerate(st.session_state.savings_goals):
            with st.expander(f"🎯 {goal['name']} - ${goal['current_amount']:,.0f} / ${goal['target_amount']:,.0f}"):
                progress = min(goal['current_amount'] / goal['target_amount'], 1.0)
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.progress(progress)
                    remaining = goal['target_amount'] - goal['current_amount']
                    
                    if remaining <= 0:
                        st.success("🎉 Goal Completed!")
                        goal['completed'] = True
                    else:
                        st.write(f"Remaining: ${remaining:,.2f} ({progress*100:.1f}% complete)")
                    
                    if goal['description']:
                        st.write(f"*{goal['description']}*")
                
                with col2:
                    new_amount = st.number_input(f"Update Amount:", 
                                               value=float(goal['current_amount']),
                                               min_value=0.0, step=10.0, 
                                               key=f"goal_update_{i}")
                    
                    if st.button("💾 Update", key=f"update_goal_{i}"):
                        st.session_state.savings_goals[i]['current_amount'] = new_amount
                        st.success("Goal updated!")
                        st.rerun()
                    
                    if st.button("❌ Delete", key=f"delete_goal_{i}"):
                        st.session_state.savings_goals.pop(i)
                        st.success("Goal deleted!")
                        st.rerun()
        
        total_target = sum(goal['target_amount'] for goal in st.session_state.savings_goals)
        total_current = sum(goal['current_amount'] for goal in st.session_state.savings_goals)
        
        st.subheader("💰 Savings Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Saved", f"${total_current:,.2f}")
        with col2:
            st.metric("Total Target", f"${total_target:,.2f}")
        with col3:
            remaining = total_target - total_current
            st.metric("Remaining to Save", f"${remaining:,.2f}")
    
    if st.button("✅ Close Savings Goals"):
        st.session_state.show_savings_goals = False
        st.rerun()

def analytics_section():
    """Advanced analytics and visualizations"""
    st.header("📊 Budget Analytics & Projections")
    
    user_data = st.session_state.user_data
    actual_expenses = [e for e in st.session_state.expenses if e['amount'] > 0]
    
    if not actual_expenses:
        st.info("Add some expenses to see analytics and projections!")
        if st.button("Close Analytics"):
            st.session_state.show_analytics = False
            st.rerun()
        return
    
    if user_data['income_frequency'] == "Weekly":
        monthly_income = user_data['income_amount'] * 4.33
    elif user_data['income_frequency'] == "Fortnightly":
        monthly_income = user_data['income_amount'] * 2.167
    else:
        monthly_income = user_data['income_amount']
    
    category_spending = {}
    for expense in actual_expenses:
        cat = expense['category']
        category_spending[cat] = category_spending.get(cat, 0) + expense['amount']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💰 Spending by Category")
        if category_spending:
            chart_data = pd.DataFrame({
                'Category': list(category_spending.keys()),
                'Spent': list(category_spending.values())
            })
            st.bar_chart(chart_data.set_index('Category'))
    
    with col2:
        st.subheader("📈 Budget vs Reality")
        budget_vs_actual = []
        for cat in user_data['categories']:
            budget = user_data['category_budgets'][cat]
            spent = category_spending.get(cat, 0)
            budget_vs_actual.append({
                'Category': cat,
                'Budget': budget,
                'Spent': spent,
                'Remaining': budget - spent
            })
        
        comparison_df = pd.DataFrame(budget_vs_actual)
        st.bar_chart(comparison_df.set_index('Category')[['Budget', 'Spent']])
    
    st.subheader("🔮 Monthly Projections")
    
    total_spent = sum(category_spending.values())
    days_in_month = 30
    current_day = datetime.now().day
    
    if current_day > 0:
        daily_avg_spending = total_spent / current_day
        projected_monthly_spending = daily_avg_spending * days_in_month
        projected_savings = monthly_income - projected_monthly_spending
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Spent So Far", f"${total_spent:,.2f}")
        with col2:
            st.metric("Daily Average", f"${daily_avg_spending:.2f}")
        with col3:
            st.metric("Projected Monthly Spending", f"${projected_monthly_spending:,.2f}")
        with col4:
            delta_color = "normal" if projected_savings >= 0 else "inverse"
            st.metric("Projected Savings", f"${projected_savings:,.2f}",
                     delta=f"${projected_savings:,.2f}" if projected_savings >= 0 else f"-${abs(projected_savings):,.2f}",
                     delta_color=delta_color)
        
        st.subheader("💾 Balance Projection Chart")
        
        days = list(range(1, 31))
        projected_balance = []
        running_balance = user_data['current_balance']
        
        for day in days:
            if user_data['income_frequency'] == "Monthly" and day == user_data['payment_day']:
                running_balance += user_data['income_amount']
            elif user_data['income_frequency'] == "Weekly":
                if day % 7 == (user_data['payment_day'] if isinstance(user_data['payment_day'], int) else 1):
                    running_balance += user_data['income_amount']
            elif user_data['income_frequency'] == "Fortnightly":
                if day % 14 == (user_data['payment_day'] if isinstance(user_data['payment_day'], int) else 1):
                    running_balance += user_data['income_amount']
            
            if day <= current_day:
                daily_spent = (total_spent / current_day) if current_day > 0 else 0
            else:
                daily_spent = daily_avg_spending
            
            running_balance -= daily_spent
            projected_balance.append(running_balance)
        
        balance_df = pd.DataFrame({
            'Day': days,
            'Projected Balance': projected_balance
        })
        
        st.line_chart(balance_df.set_index('Day'))
        
        st.subheader("💡 Insights")
        
        if projected_savings > 0:
            st.success(f"✅ You're on track to save ${projected_savings:,.2f} this month!")
        else:
            st.warning(f"⚠️ You're projected to overspend by ${abs(projected_savings):,.2f} this month.")
        
        if daily_avg_spending > (monthly_income / 30):
            st.error("🚨 Your daily spending exceeds your daily income!")
        else:
            st.info("💪 Your daily spending is within your daily income limits.")
    
    if st.button("✅ Close Analytics"):
        st.session_state.show_analytics = False
        st.rerun()

def user_setup_wizard():
    """Initial setup wizard for new users"""
    st.title("🚀 Welcome to Personal Budget Tracker!")
    st.write("Let's set up your budget in just a few steps.")
    
    if 'setup_categories' not in st.session_state:
        st.session_state.setup_categories = []
    if 'setup_category_budgets' not in st.session_state:
        st.session_state.setup_category_budgets = {}
    if 'setup_category_frequencies' not in st.session_state:
        st.session_state.setup_category_frequencies = {}
    
    st.header("Step 1: Financial Information")
    
    col1, col2 = st.columns(2)
    with col1:
        current_balance = st.number_input("Current Bank Balance ($):", min_value=0.0, step=0.01)
    with col2:
        income_amount = st.number_input("Income Amount ($):", min_value=0.0, step=0.01)
    
    st.header("Step 2: Income Schedule")
    col1, col2 = st.columns(2)
    
    with col1:
        income_frequency = st.selectbox("How often do you get paid?", ["Monthly", "Fortnightly", "Weekly"])
    
    with col2:
        if income_frequency == "Monthly":
            payment_day = st.selectbox("What day of the month?", list(range(1, 32)))
        else:
            payment_day = st.selectbox("What day of the week?", 
                                     ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    
    st.header("Step 3: Budget Categories")
    st.write("Add your budget categories one by one:")
    
    with st.container():
        st.subheader("➕ Add New Category")
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            new_category = st.text_input("Category Name:", placeholder="e.g., Rent, Groceries, Transport", key="new_category_input")
        with col2:
            new_amount = st.number_input("Budget ($):", min_value=0.0, step=0.01, key="new_amount_input")
        with col3:
            new_frequency = st.selectbox("Frequency:", ["Monthly", "Weekly"], key="new_frequency_input")
        with col4:
            st.write("")
            if st.button("Add Category", type="primary"):
                if new_category.strip() and new_amount > 0:
                    if new_category.strip() not in st.session_state.setup_categories:
                        st.session_state.setup_categories.append(new_category.strip())
                        st.session_state.setup_category_budgets[new_category.strip()] = new_amount
                        st.session_state.setup_category_frequencies[new_category.strip()] = new_frequency
                        st.success(f"Added {new_category.strip()}: ${new_amount:.2f} {new_frequency.lower()}")
                        st.rerun()
                    else:
                        st.error("Category already exists!")
                else:
                    st.error("Please enter both category name and budget amount.")
    
    if st.session_state.setup_categories:
        st.subheader("📋 Your Budget Categories")
        
        total_monthly_budget = 0
        
        for i, cat in enumerate(st.session_state.setup_categories):
            amount = st.session_state.setup_category_budgets[cat]
            frequency = st.session_state.setup_category_frequencies[cat]
            
            if frequency == "Weekly":
                monthly_equiv = amount * 4.33
                total_monthly_budget += monthly_equiv
            else:
                monthly_equiv = amount
                total_monthly_budget += amount
            
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.write(f"**{cat}**")
            with col2:
                st.write(f"${amount:.2f} {frequency.lower()}")
            with col3:
                if frequency == "Weekly":
                    st.write(f"(~${monthly_equiv:.2f}/month)")
                else:
                    st.write(f"(${monthly_equiv:.2f}/month)")
            with col4:
                if st.button("❌", key=f"remove_{i}", help=f"Remove {cat}"):
                    st.session_state.setup_categories.remove(cat)
                    del st.session_state.setup_category_budgets[cat]
                    del st.session_state.setup_category_frequencies[cat]
                    st.rerun()
        
        st.write("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Monthly Budget", f"${total_monthly_budget:,.2f}")
        with col2:
            if income_amount > 0:
                if income_frequency == "Weekly":
                    monthly_income = income_amount * 4.33
                elif income_frequency == "Fortnightly":
                    monthly_income = income_amount * 2.167
                else:
                    monthly_income = income_amount
                
                remaining = monthly_income - total_monthly_budget
                st.metric("Income After Budget", f"${remaining:,.2f}")
        with col3:
            if income_amount > 0:
                budget_percentage = (total_monthly_budget / monthly_income) * 100
                st.metric("Budget % of Income", f"{budget_percentage:.1f}%")
    
    st.write("---")
    if st.button("Complete Setup 🎯", type="primary", disabled=len(st.session_state.setup_categories) == 0):
        if current_balance >= 0 and income_amount > 0 and st.session_state.setup_categories:
            st.session_state.user_data = {
                'current_balance': current_balance,
                'income_amount': income_amount,
                'income_frequency': income_frequency,
                'payment_day': payment_day,
                'categories': st.session_state.setup_categories.copy(),
                'category_budgets': st.session_state.setup_category_budgets.copy(),
                'category_frequencies': st.session_state.setup_category_frequencies.copy(),
                'setup_date': datetime.now().isoformat()
            }
            st.session_state.user_setup_complete = True
            st.session_state.last_updated = datetime.now().date()
            
            del st.session_state.setup_categories
            del st.session_state.setup_category_budgets
            del st.session_state.setup_category_frequencies
            
            save_user_data()
            st.success("Setup complete! Redirecting to your dashboard...")
            st.rerun()
        else:
            st.error("Please complete all steps: enter your financial information and add at least one budget category.")
    
    if len(st.session_state.setup_categories) == 0:
        st.info("💡 Add at least one budget category to complete setup.")

def main_dashboard():
    """Main dashboard for existing users"""
    user_data = st.session_state.user_data
    
    check_and_add_income()
    
    st.title("💰 Personal Budget Tracker")
    
    with st.sidebar:
        st.header("⚙️ Manage Budget")
        
        if st.button("💰 Update Income"):
            st.session_state.show_income_update = True
        
        if st.button("📋 Manage Categories"):
            st.session_state.show_category_management = True
        
        if st.button("🎯 Savings Goals"):
            st.session_state.show_savings_goals = True
        
        if st.button("📊 View Analytics"):
            st.session_state.show_analytics = True
        
        st.write("---")
        
        # Monthly reset settings
        st.subheader("📅 Monthly Reset")
        
        if 'monthly_reset_day' not in user_data:
            st.session_state.user_data['monthly_reset_day'] = 1
        
        new_reset_day = st.selectbox(
            "Reset budget tracking on:", 
            list(range(1, 29)), 
            index=user_data.get('monthly_reset_day', 1) - 1,
            help="Choose which day of the month to start tracking a new budget period"
        )
        
        if new_reset_day != user_data.get('monthly_reset_day', 1):
            st.session_state.user_data['monthly_reset_day'] = new_reset_day
            st.success(f"Budget will reset on the {new_reset_day}th of each month")
        
        # Show current budget month
        current_month_date = datetime.strptime(st.session_state.current_month_year, "%Y-%m")
        st.write(f"**Current budget month:** {current_month_date.strftime('%B %Y')}")
        
        # Month selector for viewing different months
        available_months = get_available_months()
        if len(available_months) > 1:
            st.subheader("📊 View Month")
            month_options = []
            for month in available_months:
                month_date = datetime.strptime(month, "%Y-%m")
                if month == st.session_state.current_month_year:
                    month_options.append(f"{month_date.strftime('%B %Y')} (Current)")
                else:
                    month_options.append(month_date.strftime('%B %Y'))
            
            selected_display = st.selectbox("Select month to view:", month_options)
            
            # Convert back to month_year format
            if "(Current)" in selected_display:
                selected_month = st.session_state.current_month_year
            else:
                for month in available_months:
                    month_date = datetime.strptime(month, "%Y-%m")
                    if month_date.strftime('%B %Y') == selected_display:
                        selected_month = month
                        break
            
            if 'selected_month' not in st.session_state:
                st.session_state.selected_month = st.session_state.current_month_year
            
            if selected_month != st.session_state.selected_month:
                st.session_state.selected_month = selected_month
                st.rerun()
        else:
            st.session_state.selected_month = st.session_state.current_month_year
        
        st.write("---")
        
        st.subheader("📁 Data Management")
        
        if st.button("📤 Export Data to CSV"):
            user_data_df = pd.DataFrame([{
                'data_type': 'user_settings',
                'current_balance': user_data['current_balance'],
                'income_amount': user_data['income_amount'],
                'income_frequency': user_data['income_frequency'],
                'payment_day': str(user_data['payment_day']),
                'setup_date': user_data['setup_date'],
                'monthly_reset_day': user_data.get('monthly_reset_day', 1),
                'current_month_year': st.session_state.current_month_year,
                'categories': '|'.join(user_data['categories']),
                'category_budgets': '|'.join([f"{k}:{v}" for k, v in user_data['category_budgets'].items()]),
                'category_frequencies': '|'.join([f"{k}:{v}" for k, v in user_data['category_frequencies'].items()])
            }])
            
            expenses_df = pd.DataFrame(st.session_state.expenses)
            if not expenses_df.empty:
                expenses_df['data_type'] = 'expense'
            else:
                expenses_df = pd.DataFrame(columns=['data_type', 'date', 'category', 'amount', 'description', 'frequency'])
            
            if st.session_state.savings_goals:
                savings_df = pd.DataFrame(st.session_state.savings_goals)
                savings_df['data_type'] = 'savings_goal'
            else:
                savings_df = pd.DataFrame(columns=['data_type', 'id', 'name', 'target_amount', 'current_amount', 'description', 'created_date', 'completed'])
            
            combined_df = pd.concat([user_data_df, expenses_df, savings_df], ignore_index=True, sort=False)
            
            csv_data = combined_df.to_csv(index=False)
            st.download_button(
                label="💾 Download CSV",
                data=csv_data,
                file_name=f"budget_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        
        uploaded_file = st.file_uploader("📥 Import Data from CSV", type=['csv'])
        if uploaded_file is not None:
            if st.button("🔄 Load Data", type="primary"):
                try:
                    df = pd.read_csv(uploaded_file)
                    
                    user_settings = df[df['data_type'] == 'user_settings'].iloc[0]
                    
                    categories = user_settings['categories'].split('|') if pd.notna(user_settings['categories']) else []
                    category_budgets = {}
                    category_frequencies = {}
                    
                    if pd.notna(user_settings['category_budgets']):
                        for item in user_settings['category_budgets'].split('|'):
                            if ':' in item:
                                k, v = item.split(':', 1)
                                category_budgets[k] = float(v)
                    
                    if pd.notna(user_settings['category_frequencies']):
                        for item in user_settings['category_frequencies'].split('|'):
                            if ':' in item:
                                k, v = item.split(':', 1)
                                category_frequencies[k] = v
                    
                    payment_day_value = user_settings['payment_day']
                    if isinstance(payment_day_value, (int, float)) or (isinstance(payment_day_value, str) and payment_day_value.replace('.', '').isdigit()):
                        payment_day = int(float(payment_day_value))
                    else:
                        payment_day = str(payment_day_value)
                    
                    st.session_state.user_data = {
                        'current_balance': float(user_settings['current_balance']),
                        'income_amount': float(user_settings['income_amount']),
                        'income_frequency': user_settings['income_frequency'],
                        'payment_day': payment_day,
                        'setup_date': user_settings['setup_date'],
                        'monthly_reset_day': int(user_settings.get('monthly_reset_day', 1)),
                        'categories': categories,
                        'category_budgets': category_budgets,
                        'category_frequencies': category_frequencies
                    }
                    
                    # Restore current month year if available
                    if 'current_month_year' in user_settings and pd.notna(user_settings['current_month_year']):
                        st.session_state.current_month_year = user_settings['current_month_year']
                    else:
                        # Default to current month if not in saved data
                        today = datetime.now()
                        st.session_state.current_month_year = f"{today.year}-{today.month:02d}"
                    
                    expenses_data = df[df['data_type'] == 'expense']
                    st.session_state.expenses = []
                    
                    for _, expense in expenses_data.iterrows():
                        if pd.notna(expense['date']) and pd.notna(expense['category']):
                            st.session_state.expenses.append({
                                'date': expense['date'],
                                'category': expense['category'],
                                'amount': float(expense['amount']) if pd.notna(expense['amount']) else 0.0,
                                'description': expense['description'] if pd.notna(expense['description']) else '',
                                'frequency': expense['frequency'] if pd.notna(expense['frequency']) else 'Monthly'
                            })
                    
                    savings_data = df[df['data_type'] == 'savings_goal']
                    st.session_state.savings_goals = []
                    
                    for _, goal in savings_data.iterrows():
                        if pd.notna(goal.get('name')):
                            st.session_state.savings_goals.append({
                                'id': int(goal.get('id', 0)),
                                'name': goal['name'],
                                'target_amount': float(goal.get('target_amount', 0)),
                                'current_amount': float(goal.get('current_amount', 0)),
                                'description': goal.get('description', ''),
                                'created_date': goal.get('created_date', datetime.now().isoformat()),
                                'completed': bool(goal.get('completed', False))
                            })
                    
                    st.session_state.user_setup_complete = True
                    st.session_state.last_updated = datetime.now().date()
                    
                    st.success("✅ Data loaded successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error loading data: {str(e)}")
                    st.error("Please make sure you're uploading a valid budget tracker CSV file.")
        
        st.write("---")
        st.write("**Setup Date:**")
        setup_date = datetime.fromisoformat(user_data['setup_date']).strftime("%B %d, %Y")
        st.write(setup_date)
        
        st.write("---")
        st.write("⚠️ **Data Storage Note:**")
        st.write("Data only persists during this browser session. For permanent storage, export your data regularly.")
        
        if st.button("🔄 Reset All Data", type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    if st.session_state.get('show_income_update', False):
        update_income_section()
    
    elif st.session_state.get('show_category_management', False):
        manage_categories_section()
    
    elif st.session_state.get('show_savings_goals', False):
        manage_savings_goals()
    
    elif st.session_state.get('show_analytics', False):
        analytics_section()
    
    else:
        # Check for monthly reset
        check_monthly_reset()
        
        # Use selected month for display (default to current month)
        display_month = st.session_state.get('selected_month', st.session_state.current_month_year)
        month_date = datetime.strptime(display_month, "%Y-%m")
        
        if display_month == st.session_state.current_month_year:
            st.header("📊 Financial Overview - Current Month")
        else:
            st.header(f"📊 Financial Overview - {month_date.strftime('%B %Y')}")
        
        next_payment_date = calculate_next_payment_date(user_data['income_frequency'], user_data['payment_day'])
        days_until_payment = (next_payment_date - date.today()).days
        
        next_payment_date = calculate_next_payment_date(user_data['income_frequency'], user_data['payment_day'])
        days_until_payment = (next_payment_date - date.today()).days
        
        if user_data['income_frequency'] == "Weekly":
            monthly_income = user_data['income_amount'] * 4.33
        elif user_data['income_frequency'] == "Fortnightly":
            monthly_income = user_data['income_amount'] * 2.167
        else:
            monthly_income = user_data['income_amount']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Current Balance", f"${user_data['current_balance']:,.2f}")
        with col2:
            if user_data['income_frequency'] == "Monthly":
                st.metric("Monthly Income", f"${user_data['income_amount']:,.2f}")
            else:
                st.metric(f"{user_data['income_frequency']} Income", f"${user_data['income_amount']:,.2f}")
        with col3:
            projected_balance = user_data['current_balance'] + user_data['income_amount']
            st.metric("Balance + Next Pay", f"${projected_balance:,.2f}")
        with col4:
            if days_until_payment == 0:
                st.metric("Next Payment", "Today! 🎉")
            elif days_until_payment == 1:
                st.metric("Next Payment", "Tomorrow")
            else:
                st.metric("Next Payment", f"{days_until_payment} days")
        
        st.header("📋 Budget Overview")
        
        # Add spending velocity tracker
        display_spending_velocity()
        
        total_monthly_budget = 0
        for cat in user_data['categories']:
            amount = user_data['category_budgets'][cat]
            frequency = user_data['category_frequencies'][cat]
            if frequency == "Weekly":
                total_monthly_budget += amount * 4.33
            else:
                total_monthly_budget += amount
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Monthly Budget", f"${total_monthly_budget:,.2f}")
        with col2:
            if user_data['income_amount'] > 0:
                remaining = monthly_income - total_monthly_budget
                st.metric("Income After Budget", f"${remaining:,.2f}", 
                         delta=f"${remaining:,.2f}" if remaining >= 0 else f"-${abs(remaining):,.2f}")
        with col3:
            if user_data['income_amount'] > 0:
                budget_percentage = (total_monthly_budget / monthly_income) * 100
                st.metric("Budget % of Income", f"{budget_percentage:.1f}%")
        
        st.header("💳 Add New Expense")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            expense_categories = user_data['categories'] + ["Other (No Budget)"]
            expense_category = st.selectbox("Category:", expense_categories)
        with col2:
            expense_amount = st.number_input("Amount ($):", min_value=0.0, step=0.01, key="expense_amount")
        with col3:
            expense_description = st.text_input("Description (optional):", key="expense_desc")
        
        if st.button("Add Expense", type="primary"):
            if expense_amount > 0:
                if expense_category == "Other (No Budget)":
                    expense_frequency = "Monthly"
                else:
                    expense_frequency = user_data['category_frequencies'][expense_category]
                
                expense = {
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'category': expense_category,
                    'amount': expense_amount,
                    'description': expense_description,
                    'frequency': expense_frequency
                }
                st.session_state.expenses.append(expense)
                
                st.session_state.user_data['current_balance'] -= expense_amount
                
                if expense_category == "Other (No Budget)":
                    st.success(f"Added ${expense_amount:.2f} expense to {expense_category}")
                    st.info("💡 This expense won't count against any budget category.")
                else:
                    st.success(f"Added ${expense_amount:.2f} expense to {expense_category}")
                
                st.info(f"Updated balance: ${st.session_state.user_data['current_balance']:,.2f}")
                st.rerun()
            else:
                st.error("Please enter a valid amount")
        
        if st.session_state.expenses:
            # Get expenses for the selected month
            month_expenses = get_expenses_by_month(display_month)
            
            if display_month == st.session_state.current_month_year:
                st.header("📈 Spending Analysis - Current Month")
            else:
                st.header(f"📈 Spending Analysis - {month_date.strftime('%B %Y')}")
            
            # Filter expenses for analysis (exclude income)
            actual_expenses = [e for e in month_expenses if e['amount'] > 0]
            
            if actual_expenses:
                with st.expander(f"📋 Transactions - {month_date.strftime('%B %Y')}", expanded=True):
                    st.subheader("Manage Your Transactions")
                    
                    col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 1, 1, 2, 1])
                    with col1:
                        st.write("**Date**")
                    with col2:
                        st.write("**Category**")
                    with col3:
                        st.write("**Amount**")
                    with col4:
                        st.write("**Type**")
                    with col5:
                        st.write("**Description**")
                    with col6:
                        st.write("**Action**")
                    
                    st.write("---")
                    
                    # Show transactions for selected month
                    for expense in reversed(month_expenses):
                        # Find the actual index in the full expenses list
                        expense_index = st.session_state.expenses.index(expense)
                        
                        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 1, 1, 2, 1])
                        
                        with col1:
                            st.write(expense['date'])
                        with col2:
                            st.write(expense['category'])
                        with col3:
                            if expense['amount'] < 0:
                                st.success(f"+${abs(expense['amount']):,.2f}")
                            else:
                                st.write(f"${expense['amount']:,.2f}")
                        with col4:
                            if expense['amount'] < 0:
                                st.write("Income")
                            else:
                                st.write("Expense")
                        with col5:
                            st.write(expense['description'] if expense['description'] else "-")
                        with col6:
                            # Only allow deletion if it's the current month
                            if display_month == st.session_state.current_month_year:
                                if st.button("🗑️", key=f"delete_{expense_index}", help="Delete this transaction"):
                                    if expense['amount'] > 0:
                                        st.session_state.user_data['current_balance'] += expense['amount']
                                    elif expense['amount'] < 0:
                                        st.session_state.user_data['current_balance'] -= abs(expense['amount'])
                                    
                                    st.session_state.expenses.pop(expense_index)
                                    st.success("Transaction deleted and balance updated!")
                                    st.rerun()
                            else:
                                st.write("🔒")  # Locked for past months
                
                # Calculate spending vs budget for selected month
                category_spending = {}
                other_spending = 0
                
                # For weekly categories, only count expenses from current week
                # For monthly categories, count all expenses from the selected month
                for expense in actual_expenses:
                    cat = expense['category']
                    if cat == "Other (No Budget)":
                        other_spending += expense['amount']
                    else:
                        category_spending[cat] = category_spending.get(cat, 0) + expense['amount']
                
                st.subheader(f"💰 Spending vs Budget - {month_date.strftime('%B %Y')}")
                
                # Show budgeted categories with proper weekly/monthly tracking and trend arrows
                category_trends = get_category_trends()
                
                for cat in user_data['categories']:
                    spent = category_spending.get(cat, 0)
                    budget = user_data['category_budgets'][cat]
                    frequency = user_data['category_frequencies'][cat]
                    
                    # Get trend data
                    trend_data = category_trends.get(cat, {'arrow': '➡️', 'status': 'No data', 'percent': 0})
                    
                    # For weekly categories, only show spending from current week when viewing current month
                    if frequency == "Weekly" and display_month == st.session_state.current_month_year:
                        # Get current week expenses for this category
                        current_week_expenses = get_current_week_expenses()
                        week_spent = 0
                        for expense in current_week_expenses:
                            if expense['amount'] > 0 and expense['category'] == cat:
                                week_spent += expense['amount']
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.write(f"**{cat}** {trend_data['arrow']}")
                            st.write(f"({frequency} - This Week)")
                            if trend_data['status'] != 'No data':
                                st.caption(f"Trend: {trend_data['status']}")
                        with col2:
                            st.write(f"Budget: ${budget:.2f}")
                        with col3:
                            st.write(f"Spent: ${week_spent:.2f}")
                        with col4:
                            remaining = budget - week_spent
                            if remaining >= 0:
                                st.success(f"Remaining: ${remaining:.2f}")
                            else:
                                st.error(f"Over budget: ${abs(remaining):.2f}")
                        
                        # Progress bar
                        if budget > 0:
                            progress = min(week_spent / budget, 1.0)
                            st.progress(progress)
                        else:
                            st.progress(0)
                    
                    else:
                        # Monthly categories or viewing past months
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.write(f"**{cat}** {trend_data['arrow']}")
                            if frequency == "Weekly" and display_month != st.session_state.current_month_year:
                                st.write(f"({frequency} - Full Month)")
                            else:
                                st.write(f"({frequency})")
                            if trend_data['status'] != 'No data':
                                st.caption(f"Trend: {trend_data['status']}")
                        with col2:
                            if frequency == "Weekly" and display_month != st.session_state.current_month_year:
                                # Show monthly equivalent for past months
                                monthly_budget = budget * 4.33
                                st.write(f"Budget: ~${monthly_budget:.2f}")
                            else:
                                st.write(f"Budget: ${budget:.2f}")
                        with col3:
                            st.write(f"Spent: ${spent:.2f}")
                        with col4:
                            if frequency == "Weekly" and display_month != st.session_state.current_month_year:
                                monthly_budget = budget * 4.33
                                remaining = monthly_budget - spent
                            else:
                                remaining = budget - spent
                            
                            if remaining >= 0:
                                st.success(f"Remaining: ${remaining:.2f}")
                            else:
                                st.error(f"Over budget: ${abs(remaining):.2f}")
                        
                        # Progress bar
                        if frequency == "Weekly" and display_month != st.session_state.current_month_year:
                            monthly_budget = budget * 4.33
                            if monthly_budget > 0:
                                progress = min(spent / monthly_budget, 1.0)
                                st.progress(progress)
                            else:
                                st.progress(0)
                        else:
                            if budget > 0:
                                progress = min(spent / budget, 1.0)
                                st.progress(progress)
                            else:
                                st.progress(0)
                
                if other_spending > 0:
                    st.write("---")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.write("**Other (No Budget)**")
                        st.write("(Unbudgeted)")
                    with col2:
                        st.write("Budget: Not applicable")
                    with col3:
                        st.write(f"Spent: ${other_spending:.2f}")
                    with col4:
                        st.info("No budget limit")
                
                total_spent = sum(category_spending.values()) + other_spending
                st.subheader(f"📊 Monthly Summary - {month_date.strftime('%B %Y')}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Spent", f"${total_spent:,.2f}")
                with col2:
                    budget_remaining = total_monthly_budget - sum(category_spending.values())
                    st.metric("Budget Remaining", f"${budget_remaining:,.2f}")
                    if other_spending > 0:
                        st.caption(f"(+${other_spending:.2f} unbudgeted)")
                with col3:
                    if display_month == st.session_state.current_month_year:
                        st.metric("Current Balance", f"${st.session_state.user_data['current_balance']:,.2f}")
                    else:
                        st.metric("Month Status", "Archived")
                with col4:
                    if display_month == st.session_state.current_month_year:
                        money_saved = monthly_income - total_spent
                        delta_color = "normal" if money_saved >= 0 else "inverse"
                        st.metric("Money Saved This Month", f"${money_saved:,.2f}", 
                                 delta=f"${money_saved:,.2f}" if money_saved >= 0 else f"-${abs(money_saved):,.2f}",
                                 delta_color=delta_color)
                    else:
                        # For past months, show if they were over/under budget
                        money_saved = monthly_income - total_spent
                        if money_saved >= 0:
                            st.metric("Month Result", f"+${money_saved:,.2f}", "Saved money")
                        else:
                            st.metric("Month Result", f"-${abs(money_saved):,.2f}", "Over budget")
                
                # Only show savings goals for current month
                if display_month == st.session_state.current_month_year and st.session_state.savings_goals:
                    st.subheader("🎯 Savings Goals Progress")
                    
                    cols = st.columns(min(len(st.session_state.savings_goals), 3))
                    for i, goal in enumerate(st.session_state.savings_goals[:3]):
                        with cols[i % 3]:
                            progress = min(goal['current_amount'] / goal['target_amount'], 1.0)
                            st.metric(
                                goal['name'],
                                f"${goal['current_amount']:,.0f}",
                                f"{progress*100:.1f}% of ${goal['target_amount']:,.0f}"
                            )
                            st.progress(progress)
                    
                    if len(st.session_state.savings_goals) > 3:
                        st.caption(f"...and {len(st.session_state.savings_goals) - 3} more goals")
            
            else:
                if display_month == st.session_state.current_month_year:
                    st.info("Add some expenses to see your spending analysis!")
                else:
                    st.info(f"No expenses recorded for {month_date.strftime('%B %Y')}")
        else:
            st.info("Add some expenses to start tracking your spending!")

def main():
    initialize_session_state()
    load_user_data()
    
    if not st.session_state.user_setup_complete:
        st.title("💰 Personal Budget Tracker")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🚀 New User")
            if st.button("Start Fresh Setup", type="primary"):
                st.session_state.start_fresh = True
                st.rerun()
        
        with col2:
            st.subheader("📥 Returning User")
            uploaded_file = st.file_uploader("Load Your Budget Data (CSV)", type=['csv'])
            if uploaded_file is not None:
                if st.button("🔄 Load My Data", type="primary"):
                    try:
                        df = pd.read_csv(uploaded_file)
                        
                        user_settings = df[df['data_type'] == 'user_settings'].iloc[0]
                        
                        categories = user_settings['categories'].split('|') if pd.notna(user_settings['categories']) else []
                        category_budgets = {}
                        category_frequencies = {}
                        
                        if pd.notna(user_settings['category_budgets']):
                            for item in user_settings['category_budgets'].split('|'):
                                if ':' in item:
                                    k, v = item.split(':', 1)
                                    category_budgets[k] = float(v)
                        
                        if pd.notna(user_settings['category_frequencies']):
                            for item in user_settings['category_frequencies'].split('|'):
                                if ':' in item:
                                    k, v = item.split(':', 1)
                                    category_frequencies[k] = v
                        
                        payment_day_value = user_settings['payment_day']
                        if isinstance(payment_day_value, (int, float)) or (isinstance(payment_day_value, str) and payment_day_value.replace('.', '').isdigit()):
                            payment_day = int(float(payment_day_value))
                        else:
                            payment_day = str(payment_day_value)
                        
                        st.session_state.user_data = {
                            'current_balance': float(user_settings['current_balance']),
                            'income_amount': float(user_settings['income_amount']),
                            'income_frequency': user_settings['income_frequency'],
                            'payment_day': payment_day,
                            'setup_date': user_settings['setup_date'],
                            'monthly_reset_day': int(user_settings.get('monthly_reset_day', 1)),
                            'categories': categories,
                            'category_budgets': category_budgets,
                            'category_frequencies': category_frequencies
                        }
                        
                        # Restore current month year if available
                        if 'current_month_year' in user_settings and pd.notna(user_settings['current_month_year']):
                            st.session_state.current_month_year = user_settings['current_month_year']
                        else:
                            # Default to current month if not in saved data
                            today = datetime.now()
                            st.session_state.current_month_year = f"{today.year}-{today.month:02d}"
                        
                        expenses_data = df[df['data_type'] == 'expense']
                        st.session_state.expenses = []
                        
                        for _, expense in expenses_data.iterrows():
                            if pd.notna(expense['date']) and pd.notna(expense['category']):
                                st.session_state.expenses.append({
                                    'date': expense['date'],
                                    'category': expense['category'],
                                    'amount': float(expense['amount']) if pd.notna(expense['amount']) else 0.0,
                                    'description': expense['description'] if pd.notna(expense['description']) else '',
                                    'frequency': expense['frequency'] if pd.notna(expense['frequency']) else 'Monthly'
                                })
                        
                        savings_data = df[df['data_type'] == 'savings_goal']
                        st.session_state.savings_goals = []
                        
                        for _, goal in savings_data.iterrows():
                            if pd.notna(goal.get('name')):
                                st.session_state.savings_goals.append({
                                    'id': int(goal.get('id', 0)),
                                    'name': goal['name'],
                                    'target_amount': float(goal.get('target_amount', 0)),
                                    'current_amount': float(goal.get('current_amount', 0)),
                                    'description': goal.get('description', ''),
                                    'created_date': goal.get('created_date', datetime.now().isoformat()),
                                    'completed': bool(goal.get('completed', False))
                                })
                        
                        st.session_state.user_setup_complete = True
                        st.session_state.last_updated = datetime.now().date()
                        
                        st.success("✅ Welcome back! Your data has been loaded successfully!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error loading data: {str(e)}")
                        st.error("Please make sure you're uploading a valid budget tracker CSV file.")
        
        if st.session_state.get('start_fresh', False):
            user_setup_wizard()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()