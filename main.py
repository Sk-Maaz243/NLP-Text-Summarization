from flask import Flask, request, jsonify, render_template_string
from text_summarization import (
    summarize_text,
    validate_gemini_key,
    create_summary_pdf,
    get_summary_stats,
    GEMINI_MODEL,
)

import os
import re


app = Flask(__name__)

# ---------------------------------------------------------
# APP CONFIG
# ---------------------------------------------------------

MAX_TEXT_LENGTH = 1000000  # ~1 million characters


# ---------------------------------------------------------
# COMPLETE WEBSITE HTML
# ---------------------------------------------------------

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <meta
        name="description"
        content="AI-powered text summarization using Google Gemini."
    >

    <title>AI Text Summarization — NLP Engine</title>

    <style>

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --bg: #030a13;
            --panel: #071421;
            --panel-2: #0a1a2a;
            --border: rgba(0, 168, 255, 0.18);
            --cyan: #00a8ff;
            --cyan-light: #63d4ff;
            --text: #edf8ff;
            --muted: #8ba7ba;
            --success: #39e58c;
            --danger: #ff5d73;
        }

        body {
            min-height: 100vh;
            font-family:
                Inter,
                ui-sans-serif,
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;

            color: var(--text);

            background:
                radial-gradient(
                    circle at 15% 10%,
                    rgba(0, 168, 255, 0.10),
                    transparent 28%
                ),
                radial-gradient(
                    circle at 85% 20%,
                    rgba(0, 168, 255, 0.08),
                    transparent 28%
                ),
                linear-gradient(
                    135deg,
                    #02070d,
                    #030a13 45%,
                    #06111c
                );

            overflow-x: hidden;
        }

        body::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;

            background-image:
                linear-gradient(
                    rgba(255,255,255,0.018) 1px,
                    transparent 1px
                ),
                linear-gradient(
                    90deg,
                    rgba(255,255,255,0.018) 1px,
                    transparent 1px
                );

            background-size: 40px 40px;

            mask-image:
                linear-gradient(
                    to bottom,
                    black,
                    transparent 85%
                );
        }

        button,
        textarea,
        input {
            font: inherit;
        }

        button {
            cursor: pointer;
        }

        .page {
            width: min(1250px, calc(100% - 32px));
            margin: 0 auto;
            padding: 28px 0 50px;
        }

        /* -------------------------------------------------
           HEADER
        ------------------------------------------------- */

        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;

            padding: 16px 20px;
            margin-bottom: 30px;

            border: 1px solid var(--border);
            border-radius: 20px;

            background:
                rgba(7, 20, 33, 0.78);

            backdrop-filter: blur(18px);

            box-shadow:
                0 20px 80px rgba(0, 0, 0, 0.25);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-logo {
            width: 42px;
            height: 42px;

            display: grid;
            place-items: center;

            border-radius: 13px;

            color: #00111c;
            background: var(--cyan);

            font-weight: 900;
            letter-spacing: -1px;

            box-shadow:
                0 0 30px rgba(0, 168, 255, 0.28);
        }

        .brand-text h1 {
            font-size: 15px;
            letter-spacing: 1.7px;
            text-transform: uppercase;
        }

        .brand-text p {
            margin-top: 3px;
            color: var(--muted);
            font-size: 12px;
        }

        .engine-status {
            display: flex;
            align-items: center;
            gap: 9px;

            padding: 9px 13px;

            border: 1px solid rgba(57, 229, 140, 0.18);
            border-radius: 999px;

            color: #b9ffd9;
            background: rgba(57, 229, 140, 0.06);

            font-size: 12px;
            white-space: nowrap;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success);

            box-shadow:
                0 0 14px rgba(57, 229, 140, 0.8);
        }

        /* -------------------------------------------------
           HERO
        ------------------------------------------------- */

        .hero {
            position: relative;

            display: grid;
            grid-template-columns: 1.1fr 0.9fr;
            gap: 25px;

            padding: 40px;

            margin-bottom: 25px;

            border: 1px solid var(--border);
            border-radius: 28px;

            background:
                linear-gradient(
                    135deg,
                    rgba(7, 20, 33, 0.92),
                    rgba(4, 13, 23, 0.80)
                );

            overflow: hidden;
        }

        .hero::after {
            content: "";

            position: absolute;
            width: 420px;
            height: 420px;

            right: -160px;
            top: -180px;

            border-radius: 50%;

            border: 1px solid rgba(0, 168, 255, 0.12);

            box-shadow:
                0 0 0 40px rgba(0, 168, 255, 0.025),
                0 0 0 80px rgba(0, 168, 255, 0.018),
                0 0 0 120px rgba(0, 168, 255, 0.012);

            pointer-events: none;
        }

        .hero-copy {
            position: relative;
            z-index: 2;
        }

        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 8px;

            padding: 7px 11px;

            border: 1px solid rgba(0, 168, 255, 0.20);
            border-radius: 999px;

            background: rgba(0, 168, 255, 0.05);

            color: var(--cyan-light);

            font-size: 11px;
            font-weight: 800;
            letter-spacing: 1.4px;
            text-transform: uppercase;
        }

        .hero h2 {
            margin-top: 18px;

            max-width: 680px;

            font-size: clamp(36px, 5vw, 66px);
            line-height: 0.98;
            letter-spacing: -3px;
        }

        .hero h2 span {
            color: var(--cyan);
            text-shadow:
                0 0 30px rgba(0, 168, 255, 0.24);
        }

        .hero p {
            max-width: 650px;

            margin-top: 20px;

            color: var(--muted);

            font-size: 16px;
            line-height: 1.75;
        }

        .hero-orbit {
            min-height: 280px;

            display: grid;
            place-items: center;

            position: relative;
        }

        .orbit {
            position: absolute;

            width: 230px;
            height: 230px;

            border: 1px solid rgba(0, 168, 255, 0.18);
            border-radius: 50%;

            animation: spin 15s linear infinite;
        }

        .orbit.two {
            width: 175px;
            height: 175px;

            animation-duration: 10s;
            animation-direction: reverse;

            border-color: rgba(99, 212, 255, 0.16);
        }

        .orbit.three {
            width: 120px;
            height: 120px;

            animation-duration: 7s;

            border-color: rgba(0, 168, 255, 0.20);
        }

        .orbit-dot {
            position: absolute;

            width: 9px;
            height: 9px;

            border-radius: 50%;

            background: var(--cyan);

            box-shadow:
                0 0 20px rgba(0, 168, 255, 0.9);
        }

        .orbit-dot.one {
            top: 15px;
            left: 50%;
        }

        .orbit-dot.two {
            bottom: 25px;
            right: 15px;
        }

        .orbit-dot.three {
            top: 45px;
            right: 2px;
        }

        .core {
            width: 88px;
            height: 88px;

            display: grid;
            place-items: center;

            border-radius: 28px;

            background:
                linear-gradient(
                    145deg,
                    #0d2639,
                    #06101a
                );

            border: 1px solid rgba(0, 168, 255, 0.28);

            box-shadow:
                0 0 50px rgba(0, 168, 255, 0.12),
                inset 0 0 30px rgba(0, 168, 255, 0.05);

            font-size: 31px;
        }

        @keyframes spin {
            from {
                transform: rotate(0deg);
            }

            to {
                transform: rotate(360deg);
            }
        }

        /* -------------------------------------------------
           MAIN WORKSPACE
        ------------------------------------------------- */

        .workspace {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        .panel {
            border: 1px solid var(--border);
            border-radius: 24px;

            background:
                rgba(7, 20, 33, 0.84);

            backdrop-filter: blur(18px);

            overflow: hidden;

            box-shadow:
                0 20px 70px rgba(0, 0, 0, 0.18);
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;

            padding: 19px 20px;

            border-bottom: 1px solid rgba(0, 168, 255, 0.10);
        }

        .panel-title {
            font-size: 13px;
            font-weight: 900;

            letter-spacing: 1.1px;
            text-transform: uppercase;
        }

        .panel-subtitle {
            margin-top: 4px;

            color: var(--muted);

            font-size: 11px;
        }

        .panel-body {
            padding: 20px;
        }

        /* -------------------------------------------------
           KEY AREA
        ------------------------------------------------- */

        .key-box {
            display: flex;
            gap: 10px;

            padding: 5px;

            border: 1px solid rgba(0, 168, 255, 0.15);
            border-radius: 15px;

            background: rgba(0, 0, 0, 0.15);
        }

        .key-box input {
            min-width: 0;
            flex: 1;

            border: 0;
            outline: 0;

            padding: 12px;

            color: var(--text);
            background: transparent;

            font-size: 13px;
        }

        .key-box input::placeholder {
            color: #577386;
        }

        .primary-btn {
            border: 0;
            border-radius: 11px;

            padding: 11px 17px;

            color: #00111c;

            background: var(--cyan);

            font-weight: 900;

            box-shadow:
                0 8px 25px rgba(0, 168, 255, 0.16);

            transition:
                transform 0.2s ease,
                box-shadow 0.2s ease,
                opacity 0.2s ease;
        }

        .primary-btn:hover {
            transform: translateY(-1px);

            box-shadow:
                0 12px 30px rgba(0, 168, 255, 0.24);
        }

        .primary-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .key-message {
            min-height: 18px;
            margin-top: 9px;

            color: var(--muted);

            font-size: 11px;
        }

        .key-message.success {
            color: #7dffb4;
        }

        .key-message.error {
            color: #ff8092;
        }

        /* -------------------------------------------------
           SOURCE
        ------------------------------------------------- */

        .textarea-wrap {
            position: relative;
        }

        textarea {
            width: 100%;

            min-height: 300px;

            resize: vertical;

            padding: 18px;

            border: 1px solid rgba(0, 168, 255, 0.13);
            border-radius: 16px;

            outline: none;

            color: var(--text);

            background:
                rgba(2, 8, 14, 0.65);

            line-height: 1.7;
            font-size: 14px;

            transition:
                border-color 0.2s ease,
                box-shadow 0.2s ease;
        }

        textarea:focus {
            border-color: rgba(0, 168, 255, 0.48);

            box-shadow:
                0 0 0 4px rgba(0, 168, 255, 0.05);
        }

        textarea::placeholder {
            color: #527084;
        }

        .stats {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;

            margin-top: 10px;
        }

        .stat {
            padding: 7px 10px;

            border: 1px solid rgba(0, 168, 255, 0.10);
            border-radius: 9px;

            background: rgba(0, 168, 255, 0.035);

            color: var(--muted);

            font-size: 10px;
        }

        .stat strong {
            color: var(--text);
        }

        /* -------------------------------------------------
           MODE SELECTOR
        ------------------------------------------------- */

        .mode-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);

            gap: 8px;

            margin-bottom: 14px;
        }

        .mode-btn {
            padding: 11px 8px;

            border: 1px solid rgba(0, 168, 255, 0.11);
            border-radius: 11px;

            color: var(--muted);

            background: rgba(0, 0, 0, 0.12);

            font-size: 11px;
            font-weight: 800;

            transition: all 0.2s ease;
        }

        .mode-btn:hover {
            border-color: rgba(0, 168, 255, 0.28);
            color: var(--text);
        }

        .mode-btn.active {
            color: #00111c;
            background: var(--cyan);
            border-color: var(--cyan);
        }

        .action-row {
            display: flex;
            flex-wrap: wrap;
            gap: 9px;

            margin-top: 12px;
        }

        .secondary-btn {
            padding: 10px 14px;

            border: 1px solid rgba(0, 168, 255, 0.14);
            border-radius: 11px;

            color: var(--muted);

            background: rgba(0, 0, 0, 0.12);

            font-size: 11px;
            font-weight: 800;

            transition: all 0.2s ease;
        }

        .secondary-btn:hover {
            color: var(--text);
            border-color: rgba(0, 168, 255, 0.30);
        }

        .summarize-btn {
            flex: 1;

            min-width: 180px;

            padding: 13px 18px;

            border: 0;
            border-radius: 12px;

            color: #00111c;
            background: var(--cyan);

            font-weight: 900;
            letter-spacing: 0.3px;

            box-shadow:
                0 10px 35px rgba(0, 168, 255, 0.16);
        }

        .summarize-btn:disabled {
            opacity: 0.45;
            cursor: not-allowed;
        }

        /* -------------------------------------------------
           OUTPUT
        ------------------------------------------------- */

        .output-area {
            min-height: 300px;

            padding: 18px;

            border: 1px solid rgba(0, 168, 255, 0.13);
            border-radius: 16px;

            background:
                rgba(2, 8, 14, 0.65);

            white-space: pre-wrap;

            color: #dff5ff;

            line-height: 1.75;
            font-size: 14px;

            overflow-wrap: anywhere;
        }

        .output-placeholder {
            display: grid;
            place-items: center;

            min-height: 260px;

            color: #547085;

            text-align: center;
        }

        .loader {
            width: 18px;
            height: 18px;

            border-radius: 50%;

            border: 2px solid rgba(0, 168, 255, 0.18);
            border-top-color: var(--cyan);

            animation: loading 0.8s linear infinite;

            display: inline-block;

            vertical-align: middle;

            margin-right: 8px;
        }

        @keyframes loading {
            to {
                transform: rotate(360deg);
            }
        }

        .result-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);

            gap: 8px;

            margin-top: 10px;
        }

        .result-stat {
            padding: 11px;

            border: 1px solid rgba(0, 168, 255, 0.10);
            border-radius: 12px;

            background: rgba(0, 168, 255, 0.025);
        }

        .result-stat span {
            display: block;

            color: var(--muted);

            font-size: 9px;
            text-transform: uppercase;
            letter-spacing: 0.7px;
        }

        .result-stat strong {
            display: block;

            margin-top: 4px;

            font-size: 15px;
        }

        /* -------------------------------------------------
           FOOTER
        ------------------------------------------------- */

        footer {
            margin-top: 24px;

            padding: 18px;

            color: #526d7e;

            text-align: center;

            font-size: 11px;
        }


        /* -------------------------------------------------
           GEMINI API KEY GUIDE
        ------------------------------------------------- */

        .api-guide {
            position: relative;
            margin: 0 0 25px;
            padding: 22px 24px 20px;
            border: 1px solid var(--border);
            border-radius: 24px;
            background:
                linear-gradient(
                    135deg,
                    rgba(7, 20, 33, 0.92),
                    rgba(4, 13, 23, 0.80)
                );
            box-shadow:
                0 20px 70px rgba(0, 0, 0, 0.18);
            overflow: hidden;
        }

        .api-guide::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background:
                radial-gradient(
                    circle at 50% 0%,
                    rgba(0, 168, 255, 0.08),
                    transparent 42%
                );
        }

        .api-guide-title {
            position: relative;
            z-index: 1;
            text-align: center;
            color: var(--text);
            font-size: clamp(22px, 3vw, 29px);
            font-weight: 900;
            letter-spacing: -0.7px;
        }

        .api-guide-title span {
            color: var(--cyan);
            text-shadow: 0 0 22px rgba(0, 168, 255, 0.25);
        }

        .api-guide-subtitle {
            position: relative;
            z-index: 1;
            margin-top: 5px;
            margin-bottom: 19px;
            color: var(--muted);
            text-align: center;
            font-size: 12px;
        }

        .guide-flow {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: 1fr 52px 1fr 52px 1fr;
            align-items: center;
            gap: 8px;
        }

        .guide-step {
            position: relative;
            min-width: 0;
            padding: 14px 12px 12px;
        }

        .step-number {
            position: absolute;
            top: -4px;
            left: -3px;
            width: 30px;
            height: 30px;
            display: grid;
            place-items: center;
            border-radius: 50%;
            color: #ffffff;
            background: var(--cyan);
            font-size: 13px;
            font-weight: 900;
            box-shadow: 0 0 18px rgba(0, 168, 255, 0.45);
            z-index: 3;
        }

        .step-title {
            margin-top: 155px;
            color: var(--text);
            text-align: center;
            font-size: 12px;
            font-weight: 900;
        }

        .step-text {
            margin-top: 5px;
            color: var(--muted);
            text-align: center;
            font-size: 10px;
            line-height: 1.45;
        }

        .guide-arrow {
            color: var(--cyan);
            font-size: 35px;
            font-weight: 900;
            text-align: center;
            text-shadow: 0 0 18px rgba(0, 168, 255, 0.65);
        }

        .fake-screen {
            position: absolute;
            top: 0;
            left: 12px;
            right: 12px;
            height: 132px;
            border: 1px solid rgba(0, 168, 255, 0.32);
            border-radius: 12px;
            background: #04111d;
            overflow: hidden;
            box-shadow:
                inset 0 0 25px rgba(0, 168, 255, 0.035),
                0 8px 28px rgba(0, 0, 0, 0.18);
        }

        .fake-top {
            height: 24px;
            display: flex;
            align-items: center;
            gap: 7px;
            padding: 0 9px;
            background: #071b2b;
            border-bottom: 1px solid rgba(0, 168, 255, 0.16);
            color: #8dbbd3;
            font-size: 8px;
            font-weight: 700;
        }

        .fake-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--cyan);
            box-shadow: 0 0 9px rgba(0, 168, 255, 0.8);
        }

        .fake-body {
            display: flex;
            height: 108px;
        }

        .fake-sidebar {
            width: 34%;
            padding: 8px 5px;
            border-right: 1px solid rgba(0, 168, 255, 0.12);
            background: rgba(0, 0, 0, 0.12);
        }

        .fake-menu {
            padding: 5px 6px;
            margin-bottom: 4px;
            border-radius: 5px;
            color: #668ba2;
            font-size: 7px;
            white-space: nowrap;
        }

        .fake-menu.active {
            color: #ffffff;
            background: rgba(0, 168, 255, 0.28);
            box-shadow: 0 0 10px rgba(0, 168, 255, 0.12);
        }

        .fake-content {
            flex: 1;
            min-width: 0;
            padding: 13px 11px;
        }

        .fake-content.full {
            width: 100%;
        }

        .fake-heading {
            color: #e6f7ff;
            font-size: 12px;
            font-weight: 900;
            margin-bottom: 5px;
        }

        .fake-small {
            max-width: 180px;
            color: #6e96ae;
            font-size: 7px;
            line-height: 1.45;
        }

        .fake-button {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            margin-top: 10px;
            padding: 6px 9px;
            border-radius: 6px;
            color: #00111c;
            background: var(--cyan);
            font-size: 8px;
            font-weight: 900;
            box-shadow: 0 5px 16px rgba(0, 168, 255, 0.22);
        }

        .fake-key {
            display: inline-block;
            max-width: 150px;
            margin-top: 7px;
            padding: 6px 8px;
            border: 1px solid rgba(99, 212, 255, 0.38);
            border-radius: 6px;
            color: #b9eaff;
            background: rgba(0, 0, 0, 0.18);
            font-size: 8px;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
        }

        .copy-button {
            margin-left: 4px;
        }

        .open-ai-btn {
            position: relative;
            z-index: 1;
            display: block;
            width: fit-content;
            margin: 2px auto 0;
            padding: 10px 17px;
            border: 1px solid var(--cyan);
            border-radius: 11px;
            color: var(--cyan);
            background: rgba(0, 168, 255, 0.045);
            text-decoration: none;
            font-size: 11px;
            font-weight: 900;
            transition: all 0.2s ease;
            box-shadow: 0 0 18px rgba(0, 168, 255, 0.08);
        }

        .open-ai-btn:hover {
            color: #00111c;
            background: var(--cyan);
            box-shadow: 0 0 25px rgba(0, 168, 255, 0.25);
            transform: translateY(-1px);
        }

        .guide-note {
            position: relative;
            z-index: 1;
            margin-top: 8px;
            color: #527084;
            text-align: center;
            font-size: 9px;
        }

        /* -------------------------------------------------
           CUSTOM FOOTER
        ------------------------------------------------- */

        .site-footer {
            margin-top: 28px;
            padding: 18px 18px 10px;
            border-top: 1px solid rgba(0, 168, 255, 0.13);
            color: #526d7e;
            font-size: 11px;
            line-height: 1.6;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
        }

        .footer-left,
        .footer-right {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }

        .footer-left {
            justify-content: flex-start;
        }

        .footer-right {
            justify-content: flex-end;
            text-align: right;
        }

        .footer-brand {
            color: #8ca7b8;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }

        .footer-engine {
            color: #496475;
            font-size: 10px;
        }

        .footer-signature {
            display: inline-block;
            margin-left: 6px;
            color: var(--cyan);
            text-decoration: none;
            font-family:
                "Brush Script MT",
                "Segoe Script",
                "Lucida Handwriting",
                cursive;
            font-size: 22px;
            font-style: italic;
            font-weight: 700;
            letter-spacing: 0.2px;
            text-shadow: 0 0 13px rgba(0, 168, 255, 0.30);
            transition: all 0.2s ease;
        }

        .footer-signature:hover {
            color: #ffffff;
            text-shadow: 0 0 20px rgba(0, 168, 255, 0.65);
            transform: translateY(-1px);
        }

        .footer-dot {
            margin: 0 7px;
            color: var(--cyan);
        }

        /* -------------------------------------------------
           RESPONSIVE
        ------------------------------------------------- */

        @media (max-width: 900px) {

            .hero {
                grid-template-columns: 1fr;
                padding: 28px;
            }

            .hero-orbit {
                min-height: 220px;
            }

            .workspace {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 600px) {

            .page {
                width: min(100% - 18px, 1250px);
                padding-top: 10px;
            }

            .topbar {
                padding: 12px;
                border-radius: 15px;
            }

            .engine-status {
                display: none;
            }

            .hero {
                padding: 23px 18px;
                border-radius: 20px;
            }

            .hero h2 {
                font-size: 40px;
                letter-spacing: -2px;
            }

            .panel {
                border-radius: 19px;
            }

            .panel-body {
                padding: 14px;
            }

            .mode-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .result-stats {
                grid-template-columns: repeat(2, 1fr);
            }

            .guide-flow {
                grid-template-columns: 1fr;
                gap: 5px;
            }

            .guide-arrow {
                transform: rotate(90deg);
                height: 30px;
                display: grid;
                place-items: center;
            }

            .guide-step {
                min-height: 178px;
            }

            .fake-screen {
                left: 6px;
                right: 6px;
            }

            .step-title {
                margin-top: 155px;
            }

            .api-guide {
                padding: 20px 10px 18px;
                border-radius: 19px;
            }

            .key-box {
                flex-direction: column;
            }

            .key-box .primary-btn {
                width: 100%;
            }
        }

    </style>
</head>

<body>

<div class="page">

    <!-- HEADER -->
    <header class="topbar">

        <div class="brand">

            <div class="brand-logo">
                AI
            </div>

            <div class="brand-text">

                <h1>
                    TEXT SUMMARIZATION
                </h1>

                <p>
                    AI Powered NLP Engine
                </p>

            </div>

        </div>

        <div class="engine-status">
            <span class="status-dot"></span>
            NLP ENGINE ONLINE
        </div>

    </header>


    <!-- HERO -->
    <section class="hero">

        <div class="hero-copy">

            <div class="eyebrow">
                GEMINI AI · NLP
            </div>

            <h2>
                Turn long text into
                <span>clear knowledge.</span>
            </h2>

            <p>
                Paste your text, connect your own Gemini API key,
                choose a summarization mode and generate an AI-powered
                summary without storing your API key on this website.
            </p>

        </div>


        <div class="hero-orbit">

            <div class="orbit">
                <div class="orbit-dot one"></div>
            </div>

            <div class="orbit two">
                <div class="orbit-dot two"></div>
            </div>

            <div class="orbit three">
                <div class="orbit-dot three"></div>
            </div>

            <div class="core">
                ✦
            </div>

        </div>

    </section>


    <!-- GEMINI API KEY GUIDE -->
    <section class="api-guide">

        <div class="api-guide-title">
            Need a <span>Gemini API key?</span>
        </div>

        <div class="api-guide-subtitle">
            Get it from Google AI Studio in a few clicks.
        </div>

        <div class="guide-flow">

            <!-- STEP 1 -->
            <div class="guide-step">

                <div class="step-number">1</div>

                <div class="fake-screen">
                    <div class="fake-top">
                        <span class="fake-dot"></span>
                        Google AI Studio
                    </div>

                    <div class="fake-body">
                        <div class="fake-sidebar">
                            <div class="fake-menu">⌂ Home</div>
                            <div class="fake-menu">▣ Build</div>
                            <div class="fake-menu">◉ Open models</div>
                            <div class="fake-menu active">🔑 API Keys</div>
                            <div class="fake-menu">▣ Billing</div>
                        </div>

                        <div class="fake-content">
                            <div class="fake-heading">API Keys</div>
                            <div class="fake-small">
                                Create and manage your API keys for Gemini and other Google services.
                            </div>
                        </div>
                    </div>
                </div>

                <div class="step-title">
                    Open Google AI Studio
                </div>

                <div class="step-text">
                    Open AI Studio and go to the API Keys page.
                </div>

            </div>


            <!-- ARROW -->
            <div class="guide-arrow">→</div>


            <!-- STEP 2 -->
            <div class="guide-step">

                <div class="step-number">2</div>

                <div class="fake-screen">
                    <div class="fake-top">
                        <span class="fake-dot"></span>
                        API Keys
                    </div>

                    <div class="fake-body">
                        <div class="fake-content full">
                            <div class="fake-heading">API Keys</div>
                            <div class="fake-small">
                                Create a new API key to use with Gemini and other Google services.
                            </div>

                            <div class="fake-button">
                                ＋ Create API key
                            </div>
                        </div>
                    </div>
                </div>

                <div class="step-title">
                    Click Create API key
                </div>

                <div class="step-text">
                    Create a new Gemini API key from your Google AI Studio project.
                </div>

            </div>


            <!-- ARROW -->
            <div class="guide-arrow">→</div>


            <!-- STEP 3 -->
            <div class="guide-step">

                <div class="step-number">3</div>

                <div class="fake-screen">
                    <div class="fake-top">
                        <span class="fake-dot"></span>
                        API key created
                    </div>

                    <div class="fake-body">
                        <div class="fake-content full">
                            <div class="fake-heading">API key created</div>
                            <div class="fake-small">
                                Your API key has been generated. Copy it now and store it securely.
                            </div>

                            <span class="fake-key">
                                AQzaSy••••••••••••••
                            </span>

                            <span class="fake-button copy-button">
                                ▣ Copy
                            </span>
                        </div>
                    </div>
                </div>

                <div class="step-title">
                    Copy your API key
                </div>

                <div class="step-text">
                    Copy the key and paste it into the Gemini API Key box below.
                </div>

            </div>

        </div>


        <a
            class="open-ai-btn"
            href="https://aistudio.google.com/apikey"
            target="_blank"
            rel="noopener noreferrer"
        >
            ↗ Open Google AI Studio
        </a>

        <div class="guide-note">
            Create key → copy key → paste it into the API Key box → click CONNECT.
        </div>

    </section>


    <!-- WORKSPACE -->
    <main class="workspace">


        <!-- LEFT -->
        <section class="panel">

            <div class="panel-header">

                <div>
                    <div class="panel-title">
                        Source Text
                    </div>

                    <div class="panel-subtitle">
                        Paste the content you want to summarize
                    </div>
                </div>

            </div>


            <div class="panel-body">

                <!-- API KEY -->
                <div style="margin-bottom: 18px;">

                    <div class="panel-title" style="margin-bottom: 8px;">
                        Gemini API Key
                    </div>

                    <div class="key-box">

                        <input
                            id="apiKey"
                            type="password"
                            autocomplete="off"
                            placeholder="Paste your Gemini API key"
                        >

                        <button
                            class="primary-btn"
                            id="connectBtn"
                            onclick="connectGemini()"
                        >
                            CONNECT
                        </button>

                    </div>

                    <div
                        id="keyMessage"
                        class="key-message"
                    >
                        Your key is used only for API requests and is not saved by this interface.
                    </div>

                </div>


                <!-- SOURCE TEXT -->
                <div class="textarea-wrap">

                    <textarea
                        id="sourceText"
                        placeholder="Paste an article, notes, lecture, documentation, research text or any other content here..."
                        oninput="updateStats()"
                    ></textarea>

                </div>


                <div class="stats">

                    <div class="stat">
                        Words:
                        <strong id="wordCount">0</strong>
                    </div>

                    <div class="stat">
                        Characters:
                        <strong id="charCount">0</strong>
                    </div>

                    <div class="stat">
                        Sentences:
                        <strong id="sentenceCount">0</strong>
                    </div>

                </div>


                <div class="action-row">

                    <button
                        class="secondary-btn"
                        onclick="loadSample()"
                    >
                        LOAD SAMPLE
                    </button>

                    <button
                        class="secondary-btn"
                        onclick="clearSource()"
                    >
                        CLEAR
                    </button>

                </div>

            </div>

        </section>


        <!-- RIGHT -->
        <section class="panel">

            <div class="panel-header">

                <div>

                    <div class="panel-title">
                        AI Summary
                    </div>

                    <div class="panel-subtitle">
                        Select a mode and generate your summary
                    </div>

                </div>

            </div>


            <div class="panel-body">

                <div class="mode-grid">

                    <button
                        class="mode-btn active"
                        data-mode="short"
                        onclick="selectMode(this)"
                    >
                        SHORT
                    </button>

                    <button
                        class="mode-btn"
                        data-mode="detailed"
                        onclick="selectMode(this)"
                    >
                        DETAILED
                    </button>

                    <button
                        class="mode-btn"
                        data-mode="bullet"
                        onclick="selectMode(this)"
                    >
                        BULLETS
                    </button>

                    <button
                        class="mode-btn"
                        data-mode="exam"
                        onclick="selectMode(this)"
                    >
                        EXAM NOTES
                    </button>

                </div>


                <div
                    id="output"
                    class="output-area"
                >

                    <div class="output-placeholder">
                        Your AI-generated summary will appear here.
                    </div>

                </div>


                <div
                    id="resultStats"
                    class="result-stats"
                    style="display:none;"
                >

                    <div class="result-stat">
                        <span>Original</span>
                        <strong id="originalWords">0</strong>
                    </div>

                    <div class="result-stat">
                        <span>Summary</span>
                        <strong id="summaryWords">0</strong>
                    </div>

                    <div class="result-stat">
                        <span>Saved</span>
                        <strong id="savedWords">0</strong>
                    </div>

                    <div class="result-stat">
                        <span>Reduction</span>
                        <strong id="reduction">0%</strong>
                    </div>

                </div>


                <div class="action-row">

                    <button
                        id="summarizeBtn"
                        class="summarize-btn"
                        onclick="summarize()"
                    >
                        GENERATE SUMMARY
                    </button>

                </div>


                <div class="action-row">

                    <button
                        class="secondary-btn"
                        onclick="copySummary()"
                    >
                        COPY SUMMARY
                    </button>

                    <button
                        class="secondary-btn"
                        onclick="downloadSummaryPDF()"
                    >
                        DOWNLOAD PDF
                    </button>

                    <button
                        class="secondary-btn"
                        onclick="downloadText()"
                    >
                        DOWNLOAD TXT
                    </button>

                </div>

            </div>

        </section>

    </main>


    <footer class="site-footer">

        <div class="footer-left">
            <span class="footer-brand">TEXT SUMMARIZATION</span>
            <span class="footer-dot">•</span>
            <span class="footer-engine">AI Powered NLP Engine</span>
            <span class="footer-dot">•</span>
            <span class="footer-engine">{{ model_name }}</span>
        </div>

        <div class="footer-right">
            <span>Designed &amp; Built by</span>

            <a
                class="footer-signature"
                href="https://sk-maaz243.github.io/Sk_Maaz/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Open sk_maaz portfolio"
            >
                𝓼𝓴_𝓶𝓪𝓪𝔃
            </a>

            <span class="footer-dot">•</span>
            <span id="footerDate"></span>
        </div>

    </footer>

</div>


<script>

    let selectedMode = "short";

    let configured = false;

    let lastSummary = "";

    let lastStats = null;


    const apiKeyInput =
        document.getElementById("apiKey");

    const sourceText =
        document.getElementById("sourceText");

    const output =
        document.getElementById("output");

    const summarizeBtn =
        document.getElementById("summarizeBtn");

    const connectBtn =
        document.getElementById("connectBtn");

    const keyMessage =
        document.getElementById("keyMessage");


    // Current date in the footer
    document.getElementById("footerDate").textContent =
        new Intl.DateTimeFormat("en-GB", {
            day: "2-digit",
            month: "long",
            year: "numeric"
        }).format(new Date());


    function updateStats() {

        const text = sourceText.value;

        const words =
            text.trim()
                ? text.trim().split(/\s+/).length
                : 0;

        const chars = text.length;

        const sentences =
            text.trim()
                ? (text.match(/[.!?।]+/g) || []).length
                : 0;

        document.getElementById("wordCount").textContent =
            words.toLocaleString();

        document.getElementById("charCount").textContent =
            chars.toLocaleString();

        document.getElementById("sentenceCount").textContent =
            sentences.toLocaleString();
    }


    function selectMode(button) {

        document
            .querySelectorAll(".mode-btn")
            .forEach(btn => btn.classList.remove("active"));

        button.classList.add("active");

        selectedMode =
            button.dataset.mode;
    }


    async function connectGemini() {

        const key =
            apiKeyInput.value.trim();

        if (!key) {

            showKeyMessage(
                "Please enter your Gemini API key.",
                "error"
            );

            return;
        }


        connectBtn.disabled = true;

        connectBtn.textContent = "CHECKING...";

        showKeyMessage(
            "Validating your Gemini API key...",
            ""
        );


        try {

            const response =
                await fetch("/api/configure", {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        api_key: key
                    })

                });


            const data =
                await response.json();


            if (!response.ok || !data.success) {

                configured = false;

                showKeyMessage(
                    data.error ||
                    "API key validation failed.",
                    "error"
                );

                return;
            }


            configured = true;

            showKeyMessage(
                "Gemini connected successfully.",
                "success"
            );

        } catch (error) {

            configured = false;

            showKeyMessage(
                "Could not connect to the server.",
                "error"
            );

        } finally {

            connectBtn.disabled = false;

            connectBtn.textContent = "CONNECT";
        }
    }


    function showKeyMessage(message, type) {

        keyMessage.textContent = message;

        keyMessage.className =
            "key-message " + (type || "");
    }


    async function summarize() {

        const text =
            sourceText.value.trim();


        if (!text) {

            setOutput(
                "Please paste some text first."
            );

            return;
        }


        if (!apiKeyInput.value.trim()) {

            showKeyMessage(
                "Please enter and connect your Gemini API key first.",
                "error"
            );

            return;
        }


        if (!configured) {

            const key =
                apiKeyInput.value.trim();

            connectBtn.disabled = true;

            connectBtn.textContent = "CHECKING...";

            try {

                const response =
                    await fetch("/api/configure", {

                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            api_key: key
                        })

                    });


                const data =
                    await response.json();


                if (!response.ok || !data.success) {

                    showKeyMessage(
                        data.error ||
                        "API key validation failed.",
                        "error"
                    );

                    return;
                }

                configured = true;

            } catch (error) {

                showKeyMessage(
                    "Could not connect to the server.",
                    "error"
                );

                return;

            } finally {

                connectBtn.disabled = false;

                connectBtn.textContent = "CONNECT";
            }
        }


        summarizeBtn.disabled = true;

        summarizeBtn.innerHTML =
            '<span class="loader"></span> GENERATING...';


        setOutput("");


        try {

            const response =
                await fetch("/api/summarize", {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        text: text,

                        mode: selectedMode,

                        api_key:
                            apiKeyInput.value.trim()

                    })

                });


            const data =
                await response.json();


            if (!response.ok || !data.success) {

                setOutput(
                    data.error ||
                    "Summary generation failed."
                );

                return;
            }


            lastSummary =
                data.summary || "";

            lastStats =
                data.stats || null;


            setOutput(lastSummary);

            showResultStats(lastStats);


        } catch (error) {

            setOutput(
                "Network error. Please check whether the Flask server is running."
            );

        } finally {

            summarizeBtn.disabled = false;

            summarizeBtn.textContent =
                "GENERATE SUMMARY";
        }
    }


    function setOutput(text) {

        if (!text) {

            output.innerHTML =
                '<div class="output-placeholder">' +
                'Generating your AI summary...' +
                '</div>';

            return;
        }

        output.textContent = text;
    }


    function showResultStats(stats) {

        if (!stats) return;

        document.getElementById("resultStats")
            .style.display = "grid";

        document.getElementById("originalWords")
            .textContent =
            Number(stats.original_words || 0)
                .toLocaleString();

        document.getElementById("summaryWords")
            .textContent =
            Number(stats.summary_words || 0)
                .toLocaleString();

        document.getElementById("savedWords")
            .textContent =
            Number(stats.words_saved || 0)
                .toLocaleString();

        document.getElementById("reduction")
            .textContent =
            Number(stats.reduction_percentage || 0)
                .toFixed(1) + "%";
    }


    async function copySummary() {

        if (!lastSummary) {

            alert("Generate a summary first.");

            return;
        }


        try {

            await navigator.clipboard.writeText(
                lastSummary
            );

            alert("Summary copied.");

        } catch (error) {

            alert(
                "Copy failed. Please select and copy the text manually."
            );
        }
    }


    async function downloadSummaryPDF() {

        if (!lastSummary) {

            alert("Generate a summary first.");

            return;
        }


        const original =
            sourceText.value.trim();


        try {

            const response =
                await fetch("/api/download-pdf", {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        original_text:
                            original,

                        summary:
                            lastSummary,

                        mode:
                            selectedMode

                    })

                });


            if (!response.ok) {

                const data =
                    await response.json()
                        .catch(() => ({}));

                alert(
                    data.error ||
                    "PDF generation failed."
                );

                return;
            }


            const blob =
                await response.blob();


            const url =
                window.URL.createObjectURL(blob);


            const link =
                document.createElement("a");

            link.href = url;

            link.download =
                "AI_Summary.pdf";

            document.body.appendChild(link);

            link.click();

            link.remove();

            window.URL.revokeObjectURL(url);


        } catch (error) {

            alert(
                "Could not download PDF."
            );
        }
    }


    function downloadText() {

        if (!lastSummary) {

            alert("Generate a summary first.");

            return;
        }


        const blob =
            new Blob(
                [lastSummary],
                {
                    type:
                        "text/plain;charset=utf-8"
                }
            );


        const url =
            URL.createObjectURL(blob);


        const link =
            document.createElement("a");

        link.href = url;

        link.download =
            "AI_Summary.txt";

        document.body.appendChild(link);

        link.click();

        link.remove();

        URL.revokeObjectURL(url);
    }


    function loadSample() {

        sourceText.value =
`Artificial intelligence is a branch of computer science that focuses on creating systems capable of performing tasks that normally require human intelligence. These tasks include learning, reasoning, problem solving, understanding natural language, recognizing patterns and making decisions.

Modern AI systems use techniques such as machine learning and deep learning to process large amounts of information. Machine learning allows a system to learn patterns from data instead of relying entirely on manually written rules. Deep learning uses neural networks with multiple layers and has become important for image recognition, speech processing and natural language applications.

AI is now used in many areas including education, healthcare, finance, transportation, manufacturing and customer service. However, responsible development is important because AI systems can produce incorrect results, reflect biases in training data and create privacy or security concerns.`;

        updateStats();
    }


    function clearSource() {

        sourceText.value = "";

        updateStats();

        lastSummary = "";

        lastStats = null;

        document.getElementById("resultStats")
            .style.display = "none";

        setOutput(
            "Your AI-generated summary will appear here."
        );
    }


    // Initial stats
    updateStats();

</script>

</body>
</html>
"""


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------

@app.route("/", methods=["GET"])
def home():

    return render_template_string(
        HTML,
        model_name=GEMINI_MODEL
    )


# ---------------------------------------------------------
# API KEY CONFIGURATION
# ---------------------------------------------------------

@app.route("/api/configure", methods=["POST"])
def configure_api():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        api_key = str(
            data.get("api_key", "")
        ).strip()


        if not api_key:

            return jsonify({
                "success": False,
                "error": "Gemini API key is required."
            }), 400


        validate_gemini_key(api_key)


        return jsonify({
            "success": True,
            "message": "Gemini API key is valid.",
            "model": GEMINI_MODEL
        })


    except Exception as exc:

        return jsonify({
            "success": False,
            "error": clean_error(str(exc))
        }), 400


# ---------------------------------------------------------
# SUMMARIZE API
# ---------------------------------------------------------

@app.route("/api/summarize", methods=["POST"])
def api_summarize():

    try:

        data = request.get_json(
            silent=True
        ) or {}


        text = str(
            data.get("text", "")
        ).strip()


        mode = str(
            data.get("mode", "short")
        ).strip().lower()


        api_key = str(
            data.get("api_key", "")
        ).strip()


        if not text:

            return jsonify({
                "success": False,
                "error": "Text is required."
            }), 400


        if len(text) > MAX_TEXT_LENGTH:

            return jsonify({
                "success": False,
                "error":
                    f"Text is too long. Maximum allowed size is "
                    f"{MAX_TEXT_LENGTH:,} characters."
            }), 400


        if not api_key:

            return jsonify({
                "success": False,
                "error":
                    "Please provide your Gemini API key."
            }), 400


        allowed_modes = {
            "short",
            "detailed",
            "bullet",
            "exam"
        }


        if mode not in allowed_modes:

            mode = "short"


        summary = summarize_text(
                text=text,
                mode=mode,
                api_key=api_key
            )


        stats = get_summary_stats(
                original_text=text,
                summary=summary
            )


        return jsonify({
            "success": True,
            "summary": summary,
            "mode": mode,
            "model": GEMINI_MODEL,
            "stats": stats
        })


    except Exception as exc:

        return jsonify({
            "success": False,
            "error": clean_error(str(exc))
        }), 500


# ---------------------------------------------------------
# PDF API
# ---------------------------------------------------------

@app.route("/api/download-pdf", methods=["POST"])
def api_download_pdf():

    try:

        data = request.get_json(
            silent=True
        ) or {}


        original_text = str(
            data.get("original_text", "")
        ).strip()


        summary = str(
            data.get("summary", "")
        ).strip()


        mode = str(
            data.get("mode", "short")
        ).strip().lower()


        if not summary:

            return jsonify({
                "success": False,
                "error":
                    "Summary is required to create a PDF."
            }), 400


        pdf_response = create_summary_pdf(
                original_text=original_text,
                summary=summary,
                mode=mode,
                engine_name=GEMINI_MODEL
            )


        return pdf_response


    except Exception as exc:

        return jsonify({
            "success": False,
            "error": clean_error(str(exc))
        }), 500


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "success": True,
        "status": "healthy",
        "service": "AI Text Summarization",
        "model": GEMINI_MODEL
    })


# ---------------------------------------------------------
# ERROR CLEANER
# ---------------------------------------------------------

def clean_error(message):

    message = str(message or "").strip()

    if not message:
        return "An unexpected error occurred."


    # Don't expose huge internal traces/messages
    message = re.sub(
        r"\s+",
        " ",
        message
    )


    if len(message) > 500:
        message = message[:500] + "..."


    return message


# ---------------------------------------------------------
# LOCAL DEVELOPMENT
# ---------------------------------------------------------

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
