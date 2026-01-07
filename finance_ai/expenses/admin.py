from django.contrib import admin
from .models import Expense


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
