# 🔐 Logout Fix - Quick Reference

## ❌ Problem
```
HTTP 405 (Method Not Allowed) when clicking logout button
```

## ✅ Solution

### **1. Update base.html (navbar)**
Replace logout link with POST form:

```html
<!-- ❌ BEFORE (Causes 405) -->
<a href="/logout/">Logout</a>

<!-- ✅ AFTER (Fixed) -->
<form method="post" action="{% url 'logout' %}">
  {% csrf_token %}
  <button type="submit">Logout</button>
</form>
```

### **2. Verify urls.py**
```python
path('logout/', auth_views.LogoutView.as_view(), name='logout'),
```

### **3. Verify settings.py**
```python
LOGOUT_REDIRECT_URL = 'login'
```

---

## 🧪 Test It

1. **Login** → Navigate to dashboard
2. **Click Username** → See dropdown with "Logout"
3. **Click Logout** → Should redirect to login page (NOT 405!)
4. **Login Again** → Can login as different user

---

## 🔍 Why Django Shows 405?

| Request Type | What Happens |
|---|---|
| GET /logout/ | ❌ 405 Method Not Allowed |
| POST /logout/ | ✅ 302 Redirect to login |

Django's `LogoutView` **only accepts POST** for security (CSRF token prevents unauthorized logouts).

---

## 🛡️ Why POST Form is Better Than Link?

✅ Requires CSRF token (security)
✅ Cannot be triggered by malicious links
✅ Session cleanup happens safely
✅ Django best practice

---

## 📋 Changes Made

| File | Change | Status |
|------|--------|--------|
| base.html | Logout link → POST form | ✅ Done |
| urls.py | No change needed | ✅ Already correct |
| settings.py | No change needed | ✅ Already correct |
| admin.py | Registered Expense model | ✅ Bonus |

---

## Terminal Output (After Fix)

```
✅ [07/Jan/2026 11:47:07] "POST /logout/ HTTP/1.1" 302 0
✅ [07/Jan/2026 11:47:08] "GET /login/ HTTP/1.1" 200 3689
```

Status codes:
- **302** = Redirect (logout successful)
- **200** = Login page loaded

---

**Fixed & Tested:** January 7, 2026 ✅
