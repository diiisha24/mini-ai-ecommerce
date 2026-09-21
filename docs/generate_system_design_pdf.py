"""One-off script: generates a one-page system design PDF for the assignment submission.
Not part of the application - lives outside app/ and is not imported anywhere."""

import textwrap

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUT_PATH = "system-design-onepager.pdf"

INK = HexColor("#1a1a2e")
MUTED = HexColor("#5a5a72")
BOX_BORDER = HexColor("#2d2d5f")
BOX_FILL = HexColor("#eef0fb")
ACCENT_FILL = HexColor("#dcefe3")
ACCENT_BORDER = HexColor("#1f6f4a")
LINE = HexColor("#8888aa")

PAGE_W, PAGE_H = letter


def draw_box(c, x, y, w, h, lines, fill=BOX_FILL, border=BOX_BORDER, fontsize=9.3, bold_first=True):
    c.setFillColor(fill)
    c.setStrokeColor(border)
    c.setLineWidth(1.1)
    c.roundRect(x, y, w, h, 5, stroke=1, fill=1)
    c.setFillColor(INK)
    n = len(lines)
    line_h = fontsize + 2.6
    total_h = n * line_h
    start_y = y + h / 2 + total_h / 2 - fontsize
    for i, line in enumerate(lines):
        font = "Helvetica-Bold" if (bold_first and i == 0) else "Helvetica"
        c.setFont(font, fontsize)
        tw = c.stringWidth(line, font, fontsize)
        c.drawString(x + w / 2 - tw / 2, start_y - i * line_h, line)


def draw_arrow(c, x1, y1, x2, y2, label=None, dash=False):
    c.setStrokeColor(LINE)
    c.setLineWidth(1.1)
    if dash:
        c.setDash(3, 2)
    else:
        c.setDash()
    c.line(x1, y1, x2, y2)
    c.setDash()
    # arrowhead
    import math

    ang = math.atan2(y2 - y1, x2 - x1)
    ah = 6
    aw = 3.2
    c.setFillColor(LINE)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(
        x2 - ah * math.cos(ang) + aw * math.sin(ang),
        y2 - ah * math.sin(ang) - aw * math.cos(ang),
    )
    p.lineTo(
        x2 - ah * math.cos(ang) - aw * math.sin(ang),
        y2 - ah * math.sin(ang) + aw * math.cos(ang),
    )
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColor(MUTED)
        tw = c.stringWidth(label, "Helvetica-Oblique", 7)
        c.setFillColor(HexColor("#ffffff"))
        c.rect(mx - tw / 2 - 2, my - 4, tw + 4, 9, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.drawString(mx - tw / 2, my - 2, label)


def wrapped_bullets(c, x, y, w, items, fontsize=8.3, leading=11, gap=4):
    c.setFont("Helvetica", fontsize)
    c.setFillColor(INK)
    cur_y = y
    for item in items:
        wrapped = textwrap.wrap(item, width=int(w / (fontsize * 0.52)))
        for i, line in enumerate(wrapped):
            prefix = "-  " if i == 0 else "   "
            c.drawString(x, cur_y, prefix + line)
            cur_y -= leading
        cur_y -= gap
    return cur_y


def main():
    c = canvas.Canvas(OUT_PATH, pagesize=letter)

    # Header
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, 740, "System Design - Mini AI E-Commerce Application")
    c.setFont("Helvetica", 9.5)
    c.setFillColor(MUTED)
    c.drawString(40, 724, "AI Full Stack Developer Technical Assignment - Assignment 2")
    c.setFont("Helvetica", 8.3)
    c.drawString(
        40, 710,
        "Live app: mini-ai-ecommerce.vercel.app   |   Live API: mini-ai-ecommerce-backend.onrender.com   |   "
        "Repo: github.com/diiisha24/mini-ai-ecommerce",
    )
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.line(40, 700, 572, 700)

    # ---- Diagram ----
    diagram_top_label_y = 686
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(INK)
    c.drawString(40, diagram_top_label_y, "Architecture")

    # Backend hub
    backend_x, backend_y, backend_w, backend_h = 221, 515, 170, 78
    draw_box(
        c, backend_x, backend_y, backend_w, backend_h,
        ["FastAPI Backend", "(Docker, single Uvicorn process)", "RBAC - Business logic - Auth"],
        fill=BOX_FILL,
    )
    bx_c = backend_x + backend_w / 2
    b_left = backend_x
    b_right = backend_x + backend_w
    b_top = backend_y + backend_h
    b_bot = backend_y

    # Browser (left)
    browser_x, browser_y, browser_w, browser_h = 40, 530, 140, 50
    draw_box(
        c, browser_x, browser_y, browser_w, browser_h,
        ["Browser", "React + TS + Tailwind"], fill=ACCENT_FILL, border=ACCENT_BORDER,
    )
    draw_arrow(c, browser_x + browser_w, browser_y + browser_h / 2, b_left, backend_y + backend_h / 2, "REST/JSON + JWT")

    # Postgres (right)
    pg_x, pg_y, pg_w, pg_h = 432, 530, 140, 50
    draw_box(c, pg_x, pg_y, pg_w, pg_h, ["PostgreSQL", "user / product / order"], fill=ACCENT_FILL, border=ACCENT_BORDER)
    draw_arrow(c, b_right, backend_y + backend_h / 2, pg_x, pg_y + pg_h / 2, "SQLModel")

    # Google OAuth (top)
    oauth_x, oauth_y, oauth_w, oauth_h = 221, 636, 170, 42
    draw_box(c, oauth_x, oauth_y, oauth_w, oauth_h, ["Google OAuth", "verify ID token -> issue JWT"], fill=ACCENT_FILL, border=ACCENT_BORDER)
    draw_arrow(c, bx_c, oauth_y, bx_c, b_top, "login")

    # Stripe (bottom-left)
    stripe_x, stripe_y, stripe_w, stripe_h = 141, 400, 150, 45
    draw_box(c, stripe_x, stripe_y, stripe_w, stripe_h, ["Stripe", "Checkout + Webhook (INR)"], fill=ACCENT_FILL, border=ACCENT_BORDER)
    draw_arrow(c, backend_x + 35, b_bot, stripe_x + stripe_w / 2, stripe_y + stripe_h, "checkout / webhook")

    # AI Agent (bottom-right)
    ai_x, ai_y, ai_w, ai_h = 321, 400, 170, 45
    draw_box(c, ai_x, ai_y, ai_w, ai_h, ["AI Agent", "LangGraph + Gemini, per-user tools"], fill=ACCENT_FILL, border=ACCENT_BORDER)
    draw_arrow(c, backend_x + backend_w - 35, b_bot, ai_x + ai_w / 2, ai_y + ai_h, "tool calls")

    # ---- Two-column text ----
    col_top = 372
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.line(40, col_top + 10, 572, col_top + 10)

    left_x, right_x = 40, 306
    col_w = 250

    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(INK)
    c.drawString(left_x, col_top - 8, "AWS Deployment Approach")
    c.drawString(right_x, col_top - 8, "Scaling Considerations")
    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(MUTED)
    c.drawString(left_x, col_top - 19, "(not deployed for this submission - built to run locally, see README)")

    aws_items = [
        "Frontend: static Vite build on S3 + CloudFront (or Amplify Hosting).",
        "Backend: Docker image on ECS Fargate behind an Application Load "
        "Balancer; secrets from AWS Secrets Manager, never baked into the image.",
        "Database: Amazon RDS for PostgreSQL (single-AZ for this scale).",
        "Stripe webhook: ALB target must be public HTTPS (ACM cert) since "
        "Stripe calls it directly.",
        "CI/CD: GitHub Actions builds the image, pushes to ECR, deploys to "
        "ECS on merge to main.",
    ]
    scaling_items = [
        "Current ceiling, stated concretely: single Uvicorn process + "
        "SQLAlchemy's default pool = ~15 concurrent DB-bound requests "
        "before queuing - that's the real trigger point, not a guess.",
        "Backend is stateless (JWT auth, no server sessions) - scales "
        "horizontally by adding ECS tasks behind the ALB.",
        "DB: read replica for product listing; Redis cache for the catalog "
        "and for AI tool outputs (e.g. list_products) once read volume "
        "grows well past write volume.",
        "AI agent (most latency/cost-sensitive part): move chat off the "
        "request path onto SQS + an async worker under bursty load; add "
        "per-user rate limiting to cap LLM spend; track token cost per call.",
        "Stripe webhooks already idempotent under a row lock "
        "(SELECT ... FOR UPDATE) so Stripe's automatic retries can't "
        "double-process an order.",
        "Observability: structured logging + request tracing (OpenTelemetry) "
        "once traffic outgrows eyeballing logs.",
    ]

    left_end = wrapped_bullets(c, left_x, col_top - 34, col_w, aws_items)
    right_end = wrapped_bullets(c, right_x, col_top - 26, col_w, scaling_items)

    c.setFont("Helvetica-Oblique", 7.3)
    c.setFillColor(MUTED)
    c.drawString(40, 30, "Full detail: docs/system-design.md, docs/db-schema.md, docs/api.md in the repository.")

    c.showPage()
    c.save()
    print("wrote", OUT_PATH, "left_end", left_end, "right_end", right_end)


if __name__ == "__main__":
    main()
