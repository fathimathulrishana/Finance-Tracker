# 💰 AI Personal Finance & Expense Prediction System - Phase 1

A modern, beginner-friendly Django expense tracker with an intuitive UI/UX, built with Bootstrap 5, Chart.js, and responsive design.

## 🎨 Design Features

### **UI/UX Improvements (Phase 1)**
- **Modern Finance Theme**: Light background (#f8f9fa) with finance-inspired colors
  - Primary: #0d6efd (Blue)
  - Success: #198754 (Green)
  - Subtle shadows and rounded corners
  - Responsive layout for mobile/tablet/desktop

- **Beautiful Navbar**: 
  - Fixed top navbar with soft shadow
  - Icon-based navigation (speedometer, receipt, plus-circle)
  - User dropdown for logout
  - Brand icon indicating Finance AI

- **Poppins Google Font**: Modern, clean typography throughout

- **Bootstrap Icons (v1.11.1)**: Professional icons integrated:
  - Dashboard: 📊 speedometer2
  - Expenses: 🧾 receipt
  - Add: ➕ plus-circle
  - Categories: 🍔 cup-hot, 🚗 car-front, 👜 bag, 💳 credit-card
  - Actions: ✏️ pencil, 🗑️ trash

- **Centered Modals**: Login/Register pages with gradient effects
- **Card-Based Layout**: Clean cards with subtle borders and shadows
- **Footer**: Copyright and attribution

---

## 🚀 Phase 1 Features

### ✅ Core Functionality
- **User Authentication**
  - Register with email validation
  - Login/Logout with session management
  - Protected routes (@login_required)
  - User-scoped data access

- **Expense CRUD Operations**
  - Add expenses (category, amount, description)
  - View all expenses in a professional table
  - Edit expenses inline
  - Delete with confirmation
  - Month-based filtering

- **Dashboard Analytics**
  - Total monthly expenses card
  - Number of expenses card
  - Current month indicator
  - Average per expense
  - Category-wise pie chart
  - Monthly trend line chart
  - **Charts powered by Chart.js 4.4.1**

- **Responsive Design**
  - Mobile-first approach
  - Works on all screen sizes
  - Bootstrap 5 grid system
  - Touch-friendly buttons

### 📱 Templates

#### **base.html** - Master template
- Navbar with dropdowns
- Message framework integration
- Footer
- Bootstrap + Chart.js CDNs
- Custom CSS for finance theme

#### **dashboard.html** - Overview page
- 4 summary cards with icons
- Category-wise pie chart
- Monthly expense trend line chart
- Responsive 2-column layout

#### **expense_list.html** - Table view
- Professional data table
- Colored category badges:
  - 🍔 Food: Red
  - 🚗 Travel: Blue
  - 👜 Shopping: Yellow
  - 💳 Bills: Red
  - Others: Gray
- Month filter dropdown
- Edit/Delete action buttons
- Responsive table with horizontal scroll

#### **add_expense.html** - Form page
- Centered card design
- Category dropdown
- Amount input with $ prefix
- Description textarea
- Icon-labeled inputs
- Cancel button fallback

#### **login.html** - Authentication
- Centered login card with shadow
- Icon indicator (blue graph-up)
- Username and password fields
- Link to register page
- Responsive design

#### **register.html** - Sign-up page
- Centered register card with shadow
- Icon indicator (green person-plus)
- Username, email, password fields
- Password requirements helper text
- Link to login page
- Form validation messages

---

## 📊 Project Structure

```
finance_ai/
├── finance_ai/
│   ├── settings.py              # Django config (app install, templates, static)
│   ├── urls.py                  # Root URLs (auth views, includes expenses.urls)
│   └── wsgi.py
├── expenses/
│   ├── migrations/
│   │   └── 0001_initial.py     # Expense model migration
│   ├── templates/
│   │   ├── base.html           # Master template (navbar, footer, CDNs)
│   │   ├── dashboard.html      # Dashboard with 4 cards + 2 charts
│   │   ├── add_expense.html    # Form for adding/editing expenses
│   │   ├── expense_list.html   # Table with filter and CRUD buttons
│   │   ├── login.html          # Login form
│   │   ├── register.html       # Registration form
│   │   └── confirm_delete.html # Delete confirmation
│   ├── models.py               # Expense model (user, category, amount, date, description)
│   ├── views.py                # All views (auth, CRUD, dashboard)
│   ├── urls.py                 # App URLs
│   ├── forms.py                # ExpenseForm, RegisterForm, MonthFilterForm
│   └── admin.py
├── static/                      # Static files directory
├── manage.py
└── db.sqlite3                  # SQLite database

```

---

## 🛠️ Installation & Setup

### 1. **Prerequisites**
- Python 3.12+
- Windows/Mac/Linux

### 2. **Clone & Install**

```bash
cd C:\Users\HP\OneDrive\Desktop\FinanceTracker\finance_ai
```

#### Install Dependencies (if not already)
```powershell
..\.venv\Scripts\python.exe -m pip install "Django>=5.0,<6.0"
```

#### Run Migrations
```powershell
..\.venv\Scripts\python.exe manage.py makemigrations
..\.venv\Scripts\python.exe manage.py migrate
```

#### (Optional) Create Admin User
```powershell
..\.venv\Scripts\python.exe manage.py createsuperuser
# Then access http://127.0.0.1:8000/admin/ to manage expenses
```

### 3. **Start Development Server**

```powershell
..\.venv\Scripts\python.exe manage.py runserver
```

Open browser → http://127.0.0.1:8000

---

## 📖 How to Use

### **1. Register**
- Click **Sign Up** → Fill form → Click **Create Account**
- You'll be logged in automatically and sent to dashboard

### **2. Add Expense**
- Click **Add Expense** in navbar
- Select category (Food, Travel, Shopping, Bills, Others)
- Enter amount (e.g., 25.50)
- Add description (optional)
- Click **Save Expense**

### **3. View Expenses**
- Click **Expenses** in navbar
- See all your transactions in a table
- Use **Filter by Month** dropdown to narrow down results
- Click **Clear** to reset filter

### **4. Edit/Delete**
- In expense list, click ✏️ **Edit** to modify
- Click 🗑️ **Delete** to remove (with confirmation)

### **5. Dashboard**
- Click **Dashboard** to see overview
- View 4 summary cards:
  - Total Monthly Expense (💰 blue)
  - Number of Expenses (🧾 green)
  - Current Month (📅 yellow)
  - Avg. per Expense (📈 cyan)
- Interactive charts:
  - Pie chart: Category breakdown
  - Line chart: Monthly trend

### **6. Logout**
- Click username dropdown → **Logout**
- Redirected to login page

---

## 🎨 Color & Design Palette

| Element | Color | Purpose |
|---------|-------|---------|
| Primary Button | #0d6efd (Blue) | CTAs, main actions |
| Success Card | #198754 (Green) | Positive metrics |
| Warning Card | #ffc107 (Yellow) | Alerts, neutrals |
| Info Card | #17a2b8 (Cyan) | Additional info |
| Background | #f8f9fa (Light) | Clean, minimal look |
| Cards | White | Content containers |
| Shadow | rgba(0,0,0,0.1) | Depth, hierarchy |
| Font | Poppins (Google) | Modern, friendly |

### **Category Badge Colors**
- 🍔 **Food**: #dc3545 (Red)
- 🚗 **Travel**: #0d6efd (Blue)
- 👜 **Shopping**: #ffc107 (Yellow)
- 💳 **Bills**: #dc3545 (Red)
- ❓ **Others**: #6c757d (Gray)

---

## 🔒 Security Features

✅ **User Authentication**
- Django built-in auth system
- Password hashing (PBKDF2)
- Session management
- CSRF protection on all forms

✅ **Data Privacy**
- All queries filtered by `user=request.user`
- Users can only see their own expenses
- Delete/Edit verification (ownership check)
- Login required on all expense pages

---

## 📱 Responsive Breakpoints

| Device | Breakpoint | Layout |
|--------|-----------|--------|
| Mobile | < 768px | Single column, full-width cards |
| Tablet | 768px - 1024px | 2 columns, flexible layout |
| Desktop | > 1024px | 3-4 columns, optimized spacing |

---

## 🚫 Known Limitations (By Design - Phase 1)

❌ NO Machine Learning
❌ NO AI predictions
❌ NO anomaly detection
❌ NO receipt upload/OCR
❌ NO export to CSV/PDF
❌ NO recurring expenses
❌ NO budgets/alerts
❌ NO multi-currency support
❌ NO dark mode

*(These features planned for Phase 2+)*

---

## 🐛 Troubleshooting

### **"No expenses found" on dashboard**
- Create your first expense via **Add Expense** button
- Make sure you're viewing current month

### **Logout button not working**
- LogoutView requires POST method
- Use the dropdown menu or navigate to `/logout/` with a POST form

### **Charts not displaying**
- Check browser console for JavaScript errors
- Ensure Chart.js CDN is loaded (check `<script>` in base.html)
- Verify expense data exists for charts to render

### **404 on static files**
- Run `python manage.py collectstatic` (not needed for development)
- STATICFILES_DIRS is configured in settings.py

### **"Permission denied" errors**
- Ensure you're logged in (`@login_required` protects expense routes)
- Users can only access their own data

---

## 🎓 Learning Notes for Beginners

### **Django Concepts Used**
1. **Models** → Define Expense with ForeignKey to User
2. **Forms** → ModelForm for validation, UserCreationForm for auth
3. **Views** → @login_required decorator, get_object_or_404 for security
4. **Templates** → {% extends %}, {% if %}, template tags
5. **Auth System** → Django's built-in User model and LoginView/LogoutView
6. **Query Optimization** → .filter(), .aggregate(), TruncMonth() for grouping

### **Bootstrap 5 Patterns**
- `.card` → Content containers with soft shadows
- `.btn-primary`, `.btn-success` → Semantic button colors
- `.container-fluid`, `.row`, `.col-*` → Responsive grid
- `.table-hover`, `.table-light` → Professional tables
- `.dropdown` → User menu
- `.alert` → Messages framework

### **Chart.js Basics**
- `new Chart(ctx, {type: 'pie', data: {...}})` → Create chart
- `.aggregate(Sum())` → Backend aggregation
- `|safe` filter → Prevent HTML escaping of JSON data
- `responsive: true` → Auto-resize with container

---

## 📚 Next Steps (Phase 2)

When ready for Phase 2, plan to add:
1. ✨ AI expense categorization
2. 🤖 Spending predictions
3. 📈 Budget alerts
4. 📊 Advanced analytics
5. 📤 CSV export
6. 🔔 Notifications
7. 📱 Mobile app

---

## 📄 License

This is a personal project for learning Django. Feel free to fork and modify!

---

## 🙋 Support

If you encounter issues:
1. Check the **Troubleshooting** section above
2. Review Django logs in terminal
3. Verify all migrations ran: `python manage.py showmigrations`
4. Restart dev server: `python manage.py runserver`

---

**Built with ❤️ using Django, Bootstrap 5, and Chart.js**

*Last Updated: January 2026*
