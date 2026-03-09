import flet as ft

def main(page: ft.Page):
    page.title = "مثال القائمة الجانبية الثابتة"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True  # <--- Enable Right-to-Left layout for the entire page
    page.fonts = {"Cairo": "https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap"}
    page.theme = ft.Theme(font_family="Cairo")

    # 1. Define the NavigationRail
    # Set extended=True to keep it expanded (showing labels)
    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        extended=True,  # <--- This forces the rail to be expanded
        min_width=100,
        min_extended_width=200,
        # leading=...  <--- Do NOT add a toggle button here if you want it fixed
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.icons.DASHBOARD_OUTLINED,
                selected_icon=ft.icons.DASHBOARD,
                label="لوحة التحكم"
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.ANALYTICS_OUTLINED,
                selected_icon=ft.icons.ANALYTICS,
                label="التحليل"
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.SETTINGS_OUTLINED,
                selected_icon=ft.icons.SETTINGS,
                label="الإعدادات"
            ),
        ],
        on_change=lambda e: print("Selected destination:", e.control.selected_index),
    )

    # 2. Layout
    # Use a Row to place the Rail side-by-side with content
    page.add(
        ft.Row(
            [
                rail,
                ft.VerticalDivider(width=1),
                ft.Column(
                    [
                        ft.Text("منطقة المحتوى الرئيسية", size=30, weight=ft.FontWeight.BOLD),
                        ft.Text("القائمة الجانبية ثابتة ولا يمكن طيها.", color="grey", size=16),
                        ft.TextField(label="تجربة إدخال نص", hint_text="اكتب هنا..."),
                    ], 
                    alignment=ft.MainAxisAlignment.START, 
                    expand=True
                ),
            ],
            expand=True,
        )
    )

if __name__ == "__main__":
    # Ensure you have flet installed: pip install flet
    ft.app(target=main)
