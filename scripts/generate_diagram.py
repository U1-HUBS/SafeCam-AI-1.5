"""
Generate high-resolution DFD Level 0 Context Diagrams for SafeCam AI.
Outputs both PNG (300 DPI) and SVG formats in Classic and Modern styles.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle
import os

def create_context_diagram(output_png_path, output_svg_path, modern_style=False):
    fig, ax = plt.subplots(figsize=(11, 8.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect('equal')
    ax.axis('off')

    font_family = 'Segoe UI'
    
    bg_color = "#f8fafc" if modern_style else "#ffffff"
    frame_border = "#334155" if modern_style else "#000000"
    fig.patch.set_facecolor(bg_color)

    # Outer frame
    if modern_style:
        frame = FancyBboxPatch(
            (3.5, 3.5), 93, 93,
            boxstyle="round,pad=0.2,rounding_size=2.0",
            linewidth=2.0,
            edgecolor=frame_border,
            facecolor="#ffffff",
            zorder=1
        )
    else:
        frame = patches.Rectangle(
            (4, 4), 92, 92,
            linewidth=2.5,
            edgecolor="#000000",
            facecolor="#ffffff",
            zorder=1
        )
    ax.add_patch(frame)

    # Center Process Node: SafeCam AI
    center_x, center_y = 50, 50
    radius = 11.5

    if modern_style:
        # Subtle glow ring
        glow = Circle(
            (center_x, center_y), radius + 1.2,
            facecolor="#fee2e2",
            edgecolor="#fca5a5",
            linewidth=1.2,
            zorder=2
        )
        ax.add_patch(glow)
        center_circle = Circle(
            (center_x, center_y), radius,
            facecolor="#dc2626",
            edgecolor="#991b1b",
            linewidth=2.2,
            zorder=3
        )
    else:
        center_circle = Circle(
            (center_x, center_y), radius,
            facecolor="#d92525",
            edgecolor="#000000",
            linewidth=2.2,
            zorder=3
        )
    ax.add_patch(center_circle)

    ax.text(
        center_x, center_y,
        "SafeCam AI",
        ha='center', va='center',
        fontsize=16.5, fontweight='bold',
        color='#ffffff',
        fontfamily=font_family,
        zorder=4
    )

    # Box dimensions
    h_box_w, h_box_h = 17, 15
    v_box_w, v_box_h = 21, 14

    # External Entities
    boxes = {
        'cctv': {
            'x': 6.5, 'y': center_y - h_box_h/2, 'w': h_box_w, 'h': h_box_h,
            'title': "CCTV\nCamera\nModule",
            'cx': 6.5 + h_box_w/2, 'cy': center_y,
            'tag': "Video Source"
        },
        'security': {
            'x': 93.5 - h_box_w, 'y': center_y - h_box_h/2, 'w': h_box_w, 'h': h_box_h,
            'title': "Security\nOperator\nModule",
            'cx': 93.5 - h_box_w/2, 'cy': center_y,
            'tag': "Human Review"
        },
        'notification': {
            'x': center_x - v_box_w/2, 'y': 93.5 - v_box_h, 'w': v_box_w, 'h': v_box_h,
            'title': "Notification\nModule",
            'cx': center_x, 'cy': 93.5 - v_box_h/2,
            'tag': "Alert Dispatch"
        },
        'admin': {
            'x': center_x - v_box_w/2, 'y': 6.5, 'w': v_box_w, 'h': v_box_h,
            'title': "Admin\nModule",
            'cx': center_x, 'cy': 6.5 + v_box_h/2,
            'tag': "Config & Analytics"
        }
    }

    # Draw entity boxes
    for key, b in boxes.items():
        if modern_style:
            box_patch = FancyBboxPatch(
                (b['x'], b['y']), b['w'], b['h'],
                boxstyle="round,pad=0.2,rounding_size=1.2",
                linewidth=2.0,
                edgecolor="#2563eb",
                facecolor="#eff6ff",
                zorder=3
            )
        else:
            box_patch = patches.Rectangle(
                (b['x'], b['y']), b['w'], b['h'],
                linewidth=2.2,
                edgecolor="#000000",
                facecolor="#ffffff",
                zorder=3
            )
        ax.add_patch(box_patch)

        ax.text(
            b['cx'], b['cy'],
            b['title'],
            ha='center', va='center',
            fontsize=12, fontweight='bold',
            color='#1e3a8a' if modern_style else '#000000',
            fontfamily=font_family,
            linespacing=1.2,
            zorder=4
        )

    # Arrow drawer using annotate
    def draw_arrow(start, end, label, label_pos, align=('center', 'center')):
        arrow_color = "#1e293b" if modern_style else "#000000"
        ax.annotate(
            '',
            xy=end,
            xytext=start,
            arrowprops=dict(
                arrowstyle='-|>,head_width=0.35,head_length=0.55',
                lw=2.0,
                color=arrow_color,
                shrinkA=0,
                shrinkB=0
            ),
            zorder=3
        )

        ax.text(
            label_pos[0], label_pos[1],
            label,
            ha=align[0], va=align[1],
            fontsize=10.5, fontweight='bold',
            color=arrow_color,
            fontfamily=font_family,
            linespacing=1.15,
            zorder=5,
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#ffffff', edgecolor='#e2e8f0', alpha=0.92) if modern_style else None
        )

    # Calculate exact circle intersections
    dy = 3.0
    dx_circle = (radius**2 - dy**2)**0.5
    circle_left_x = center_x - dx_circle
    circle_right_x = center_x + dx_circle

    dx = 3.5
    dy_circle = (radius**2 - dx**2)**0.5
    circle_top_y = center_y + dy_circle
    circle_bottom_y = center_y - dy_circle

    # --- LEFT: CCTV Camera Module <-> SafeCam AI ---
    cctv_right = boxes['cctv']['x'] + boxes['cctv']['w']
    # 1. CCTV -> SafeCam AI ("Live Video Stream")
    draw_arrow(
        (cctv_right, center_y + dy),
        (circle_left_x, center_y + dy),
        "Live Video\nStream",
        ((cctv_right + circle_left_x)/2, center_y + dy + 1.2),
        align=('center', 'bottom')
    )
    # 2. SafeCam AI -> CCTV ("Watchdog Status")
    draw_arrow(
        (circle_left_x, center_y - dy),
        (cctv_right, center_y - dy),
        "Watchdog\nStatus",
        ((cctv_right + circle_left_x)/2, center_y - dy - 1.2),
        align=('center', 'top')
    )

    # --- RIGHT: SafeCam AI <-> Security Operator Module ---
    sec_left = boxes['security']['x']
    # 3. SafeCam AI -> Security ("Dispatch Alert & Clip")
    draw_arrow(
        (circle_right_x, center_y + dy),
        (sec_left, center_y + dy),
        "Dispatch\nAlert & Clip",
        ((circle_right_x + sec_left)/2, center_y + dy + 1.2),
        align=('center', 'bottom')
    )
    # 4. Security -> SafeCam AI ("Acknowledge Triage")
    draw_arrow(
        (sec_left, center_y - dy),
        (circle_right_x, center_y - dy),
        "Acknowledge\nTriage",
        ((circle_right_x + sec_left)/2, center_y - dy - 1.2),
        align=('center', 'top')
    )

    # --- TOP: SafeCam AI <-> Notification Module ---
    notif_bottom = boxes['notification']['y']
    # 5. SafeCam AI -> Notification ("Trigger Notification")
    draw_arrow(
        (center_x - dx, circle_top_y),
        (center_x - dx, notif_bottom),
        "Trigger\nNotification",
        (center_x - dx - 1.2, (circle_top_y + notif_bottom)/2),
        align=('right', 'center')
    )
    # 6. Notification -> SafeCam AI ("Report Status")
    draw_arrow(
        (center_x + dx, notif_bottom),
        (center_x + dx, circle_top_y),
        "Report\nStatus",
        (center_x + dx + 1.2, (circle_top_y + notif_bottom)/2),
        align=('left', 'center')
    )

    # --- BOTTOM: SafeCam AI <-> Admin Module ---
    admin_top = boxes['admin']['y'] + boxes['admin']['h']
    # 7. Admin -> SafeCam AI ("System & AI Config")
    draw_arrow(
        (center_x - dx, admin_top),
        (center_x - dx, circle_bottom_y),
        "System &\nAI Config",
        (center_x - dx - 1.2, (admin_top + circle_bottom_y)/2),
        align=('right', 'center')
    )
    # 8. SafeCam AI -> Admin ("Management Reports")
    draw_arrow(
        (center_x + dx, circle_bottom_y),
        (center_x + dx, admin_top),
        "Management\nReports",
        (center_x + dx + 1.2, (admin_top + circle_bottom_y)/2),
        align=('left', 'center')
    )

    plt.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    
    os.makedirs(os.path.dirname(os.path.abspath(output_png_path)), exist_ok=True)
    plt.savefig(output_png_path, dpi=300, bbox_inches='tight', pad_inches=0.1, facecolor=bg_color)
    plt.savefig(output_svg_path, format='svg', bbox_inches='tight', pad_inches=0.1, facecolor=bg_color)
    plt.close()
    print(f"Successfully generated:\n- {output_png_path}\n- {output_svg_path}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Classic Academic / Standard Style (Matching uploaded image)
    classic_png = os.path.join(base_dir, "safecam_ai_context_diagram.png")
    classic_svg = os.path.join(base_dir, "safecam_ai_context_diagram.svg")
    create_context_diagram(classic_png, classic_svg, modern_style=False)

    # 2. Modern Polished Presentation Style
    modern_png = os.path.join(base_dir, "safecam_ai_context_diagram_modern.png")
    modern_svg = os.path.join(base_dir, "safecam_ai_context_diagram_modern.svg")
    create_context_diagram(modern_png, modern_svg, modern_style=True)
