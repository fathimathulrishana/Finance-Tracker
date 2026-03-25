from django.contrib import admin
from .models import Expense, Bill, Budget


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'user', 'category', 'amount', 'description')
    list_filter = ('category', 'date', 'user')
    search_fields = ('user__username', 'description')
    readonly_fields = ('date',)

    def get_queryset(self, request):
        """Allow users to see only their own expenses in admin."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('due_date', 'user', 'title', 'category', 'amount', 'is_paid')
    list_filter = ('category', 'is_paid', 'due_date', 'user')
    search_fields = ('user__username', 'title')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'monthly_budget', 'created_at')
    list_filter = ('category', 'user')
    search_fields = ('user__username', 'category')
