import matplotlib
matplotlib.use('Agg') # Use non-interactive backend
import matplotlib.pyplot as plt
import os

def generate_performance_chart(test_id, beg_correct, beg_total, int_correct, int_total, prof_correct, prof_total):
    # Calculate percentages
    beg_pct = (beg_correct / beg_total * 100) if beg_total > 0 else 0
    int_pct = (int_correct / int_total * 100) if int_total > 0 else 0
    prof_pct = (prof_correct / prof_total * 100) if prof_total > 0 else 0
    
    stages = ['Beginner (Easy)', 'Intermediate (Hard)', 'Professional (Trick)']
    percentages = [beg_pct, int_pct, prof_pct]
    
    # Modern styling
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=90)
    
    # Set background color properties to match glassmorphism / dark theme
    fig.patch.set_facecolor('#0f172a') # Slate 900
    ax.set_facecolor('#1e293b') # Slate 800
    
    # Custom vibrant colors
    # Cyber blue, Cyber purple, Cyber pink/magenta
    colors = ['#38bdf8', '#a855f7', '#ec4899']
    
    bars = ax.bar(stages, percentages, color=colors, width=0.55, edgecolor='#0f172a', linewidth=1.5,
                  zorder=3)
    
    # Add neon-like soft shadows/glow by overlaying slightly translucent wider bars (optional/simulated)
    # Customize grid
    ax.grid(color='#334155', linestyle='--', linewidth=0.5, zorder=0)
    
    # Set labels and title
    ax.set_title("Performance Analysis by Stage", fontsize=14, pad=20, fontweight='bold', color='#f8fafc')
    ax.set_ylabel("Accuracy Percentage (%)", fontsize=11, labelpad=10, color='#cbd5e1')
    ax.set_ylim(0, 110)
    
    # Style tick labels
    ax.tick_params(colors='#94a3b8', labelsize=10)
    
    # Hide top and right spines
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    ax.spines['left'].set_color('#334155')
    ax.spines['bottom'].set_color('#334155')
    
    # Annotate bar heights
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 6),  # 6 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold',
                    color='#f1f5f9')
        
    # Ensure static directory exists
    charts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    filename = f'test_{test_id}.png'
    filepath = os.path.join(charts_dir, filename)
    
    plt.tight_layout()
    plt.savefig(filepath, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    
    return f'/static/charts/{filename}'
