import os
import cv2
import numpy as np
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parent

def create_synthetic_video(filename: str, has_altercation: bool = False, duration_sec: int = 12, fps: int = 20):
    output_path = str(SAMPLE_DIR / filename)
    width, height = 640, 480
    total_frames = duration_sec * fps
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Base background (hallway simulation with walls and floor)
    bg = np.zeros((height, width, 3), dtype=np.uint8)
    bg[:300, :] = [180, 190, 200]  # Wall color
    bg[300:, :] = [90, 95, 100]    # Floor color
    
    # Door frames / perspective lines
    cv2.line(bg, (0, 300), (640, 300), (60, 60, 60), 2)
    cv2.rectangle(bg, (100, 160), (180, 300), (130, 140, 150), -1)
    cv2.rectangle(bg, (460, 160), (540, 300), (130, 140, 150), -1)

    print(f"Generating synthetic video: {output_path} (has_altercation={has_altercation})...")

    for i in range(total_frames):
        t = i / fps
        frame = bg.copy()

        # Frame timestamp overlay
        cv2.putText(
            frame,
            f"SIMULATED CCTV | TIME: {t:05.2f}s | FPS: {fps}",
            (15, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1
        )

        # Normal walking person 1 (moves left to right)
        x1 = int(50 + (i * 3.5) % 540)
        y1 = 280
        cv2.circle(frame, (x1, y1 - 40), 14, (60, 80, 200), -1)  # Head
        cv2.rectangle(frame, (x1 - 10, y1 - 25), (x1 + 10, y1 + 30), (70, 120, 180), -1) # Body

        # Normal walking person 2
        x2 = int(580 - (i * 2.8) % 520)
        y2 = 290
        cv2.circle(frame, (x2, y2 - 40), 14, (180, 100, 50), -1)
        cv2.rectangle(frame, (x2 - 10, y2 - 25), (x2 + 10, y2 + 30), (150, 80, 130), -1)

        # Altercation event in middle frames (between second 4 and 9)
        if has_altercation and (4.0 <= t <= 9.0):
            # Two people grappling/fighting in the center
            shake_x = np.random.randint(-12, 13)
            shake_y = np.random.randint(-8, 9)
            fx1 = 300 + shake_x
            fy1 = 280 + shake_y
            fx2 = 330 - shake_x
            fy2 = 280 - shake_y

            # Person A aggressive posture
            cv2.circle(frame, (fx1, fy1 - 40), 15, (0, 0, 220), -1)
            cv2.rectangle(frame, (fx1 - 12, fy1 - 25), (fx1 + 12, fy1 + 30), (20, 20, 180), -1)
            # Arm thrust
            cv2.line(frame, (fx1 + 5, fy1 - 10), (fx2 - 5, fy2 - 10), (0, 0, 255), 4)

            # Person B pushed back
            cv2.circle(frame, (fx2, fy2 - 40), 15, (220, 0, 0), -1)
            cv2.rectangle(frame, (fx2 - 12, fy2 - 25), (fx2 + 12, fy2 + 30), (180, 20, 20), -1)

            # Visual activity text
            cv2.putText(
                frame,
                "SIMULATION: PHYSICAL ALTERCATION / FIGHT",
                (140, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )
        else:
            cv2.putText(
                frame,
                "STATUS: NORMAL CORRIDOR ACTIVITY",
                (180, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 200, 0),
                2
            )

        writer.write(frame)

    writer.release()
    print(f"Finished {output_path} ({os.path.getsize(output_path)} bytes).")

if __name__ == "__main__":
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    create_synthetic_video("sample_hallway.mp4", has_altercation=False, duration_sec=10)
    create_synthetic_video("sample_fight.mp4", has_altercation=True, duration_sec=14)
