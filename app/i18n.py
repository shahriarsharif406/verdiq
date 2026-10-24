"""English / Bangla UI strings. Bangladesh-first, global-ready. Usage: t("key")."""
from __future__ import annotations

import streamlit as st

S = {
    # brand / nav
    "tagline": ("Every tonne, verified once.", "প্রতিটি টন, যাচাই একবারই।"),
    "lang": ("Language", "ভাষা"),
    "nav_overview": ("Overview", "সারসংক্ষেপ"),
    "nav_recon": ("Reconciliation", "রিকনসিলিয়েশন"),
    "nav_map": ("Map & Forest Health", "মানচিত্র ও বনের স্বাস্থ্য"),
    "nav_trust": ("Trust Scores", "ট্রাস্ট স্কোর"),
    "nav_network": ("Fraud Network", "জালিয়াতি নেটওয়ার্ক"),
    "nav_time": ("Time Machine", "টাইম মেশিন"),
    "nav_prepurchase": ("Pre-Purchase Check", "ক্রয়-পূর্ব যাচাই"),
    "nav_greenwash": ("Greenwashing Checker", "গ্রিনওয়াশিং যাচাই"),
    "nav_attack": ("Attack Mode", "অ্যাটাক মোড"),
    "nav_close": ("Day-End Close & Verify", "দিনশেষ ক্লোজ ও যাচাই"),
    "nav_passport": ("Tonne Passport", "টন পাসপোর্ট"),
    "nav_cases": ("Case Files", "কেস ফাইল"),
    # overview
    "hero_title": ("A verdict on every carbon credit", "প্রতিটি কার্বন ক্রেডিটের ওপর একটি রায়"),
    "hero_sub": ("Bank-grade three-way reconciliation, a blockchain firewall that makes double counting impossible, and a public Tonne Passport anyone can verify.",
                 "ব্যাংক-মানের ত্রিমুখী রিকনসিলিয়েশন, ডাবল কাউন্টিং অসম্ভব করা ব্লকচেইন ফায়ারওয়াল, এবং যে কেউ যাচাই করতে পারেন এমন টন পাসপোর্ট।"),
    "m_tonnes": ("tCO₂ protected from double counting", "ডাবল কাউন্টিং থেকে রক্ষা পাওয়া টন CO₂"),
    "m_usd": ("Fraudulent volume blocked", "আটকানো জালিয়াতি লেনদেন"),
    "m_cars": ("Cars off the road for a year", "এক বছরের জন্য সড়ক থেকে সরানো গাড়ি"),
    "m_trees": ("Tree seedlings grown 10 years", "১০ বছর বেড়ে ওঠা গাছের চারা"),
    "s_tonnes": ("tonnes of claims that would have been counted twice", "যে টনের দাবি দুইবার গণনা হতো"),
    "s_usd": ("traded or retired on invalid / duplicated credits", "অবৈধ বা দ্বিগুণ ক্রেডিটে বাণিজ্য বা অবসর"),
    "s_cars": ("4.6 tCO₂ per passenger car per year (US EPA)", "প্রতি যাত্রীগাড়িতে বছরে ৪.৬ টন CO₂ (US EPA)"),
    "s_trees": ("0.060 tCO₂ per seedling over 10 years (US EPA)", "প্রতি চারায় ১০ বছরে ০.০৬০ টন CO₂ (US EPA)"),
    "m_detect": ("Injected fraud types detected", "শনাক্ত করা জালিয়াতির ধরন"),
    "m_events": ("Ledger events reconciled", "মিলানো লেজার ইভেন্ট"),
    "m_flags": ("Integrity flags raised", "উত্থাপিত ইন্টেগ্রিটি ফ্ল্যাগ"),
    "m_blocked": ("Transactions blocked on-chain", "অন-চেইনে আটকানো লেনদেন"),
    "how_title": ("How VERDIQ works", "VERDIQ যেভাবে কাজ করে"),
    "how1": ("Reconcile", "মিলিয়ে দেখুন"),
    "how1d": ("Issuance × trades × retirements, replayed like a bank's daily close.", "ইস্যু × বাণিজ্য × অবসর, ব্যাংকের দৈনিক ক্লোজের মতো পুনরায় চালানো।"),
    "how2": ("Block", "আটকান"),
    "how2d": ("A smart-contract firewall reverts any second sale, second retirement or unissued credit.", "স্মার্ট-কন্ট্রাক্ট ফায়ারওয়াল দ্বিতীয় বিক্রি, দ্বিতীয় অবসর বা অনিস্যুকৃত ক্রেডিট বাতিল করে।"),
    "how3": ("Prove", "প্রমাণ করুন"),
    "how3d": ("Merkle-anchored closes and QR Tonne Passports let anyone verify one credit.", "মার্কল-অ্যাঙ্কর্ড ক্লোজ ও QR টন পাসপোর্টে যে কেউ একটি ক্রেডিট যাচাই করতে পারেন।"),
    "recent": ("Most severe findings", "সবচেয়ে গুরুতর ফলাফল"),
    "by_rule": ("Flags by rule", "নিয়ম অনুযায়ী ফ্ল্যাগ"),
    # generic
    "verified": ("VERIFIED", "যাচাইকৃত"),
    "risky": ("RISKY", "ঝুঁকিপূর্ণ"),
    "blocked": ("BLOCKED", "অবরুদ্ধ"),
    "safe": ("SAFE", "নিরাপদ"),
    "score": ("Trust score", "ট্রাস্ট স্কোর"),
    "why": ("Why", "কেন"),
    "evidence": ("Evidence", "প্রমাণ"),
    "download": ("Download", "ডাউনলোড"),
    "empty": ("Nothing to show yet.", "এখনো দেখানোর মতো কিছু নেই।"),
    # pages
    "recon_title": ("Three-way reconciliation", "ত্রিমুখী রিকনসিলিয়েশন"),
    "recon_sub": ("Registry issuance (voucher) × market trades (payment) × retirements (ledger), replayed chronologically.", "রেজিস্ট্রি ইস্যু × বাজার বাণিজ্য × অবসর, কালানুক্রমে পুনরায় চালানো।"),
    "map_title": ("Project map & forest health", "প্রকল্প মানচিত্র ও বনের স্বাস্থ্য"),
    "map_sub": ("Project footprints coloured by trust tier. Vegetation series are SIMULATED.", "ট্রাস্ট স্তর অনুযায়ী রঙিন প্রকল্প এলাকা। বনের সিরিজ সিমুলেটেড।"),
    "trust_title": ("Trust scores", "ট্রাস্ট স্কোর"),
    "trust_sub": ("0-100 per project and credit range: rule flags + Isolation Forest + Benford's law, each with a plain-English why.", "প্রকল্প ও ক্রেডিট রেঞ্জ প্রতি ০-১০০: নিয়ম ফ্ল্যাগ + আইসোলেশন ফরেস্ট + বেনফোর্ডের সূত্র।"),
    "net_title": ("Fraud network", "জালিয়াতি নেটওয়ার্ক"),
    "net_sub": ("Sellers, buyers and projects. Wash-trade loops and double-sold clusters glow coral. Select a node to see its flags.", "বিক্রেতা, ক্রেতা ও প্রকল্প। ওয়াশ-ট্রেড লুপ কোরাল রঙে জ্বলে।"),
    "time_title": ("Time machine", "টাইম মেশিন"),
    "time_sub": ("Replay the market month by month and watch fraud events appear at the moment they occur.", "বাজার মাসে মাসে পুনরায় চালান এবং জালিয়াতি ঘটার মুহূর্তে দেখুন।"),
    "pre_title": ("Buyer pre-purchase check", "ক্রেতার ক্রয়-পূর্ব যাচাই"),
    "pre_sub": ("Paste serial ranges or a whole portfolio. Get SAFE / RISKY / BLOCKED per range and what to replace.", "সিরিয়াল রেঞ্জ বা পুরো পোর্টফোলিও দিন। প্রতিটির জন্য নিরাপদ/ঝুঁকিপূর্ণ/অবরুদ্ধ ও বিকল্প পান।"),
    "gw_title": ("Greenwashing claim checker", "গ্রিনওয়াশিং দাবি যাচাই"),
    "gw_sub": ("Claimed vs actually retired vs retired from clean, verified credits.", "দাবি বনাম প্রকৃত অবসর বনাম পরিষ্কার ক্রেডিট থেকে অবসর।"),
    "atk_title": ("Attack Mode", "অ্যাটাক মোড"),
    "atk_sub": ("Inject a live double-sale or double-retirement. Watch the contract revert it and the engine flag it.", "লাইভ ডাবল-সেল বা ডাবল-রিটায়ারমেন্ট চালান। কন্ট্রাক্ট বাতিল করে ও ইঞ্জিন ফ্ল্যাগ করে।"),
    "atk_btn": ("LAUNCH ATTACK", "অ্যাটাক চালু করুন"),
    "atk_blocked": ("BLOCKED", "অবরুদ্ধ"),
    "close_title": ("Day-End Close & verify", "দিনশেষ ক্লোজ ও যাচাই"),
    "close_sub": ("Banks close the day. Now carbon markets do too: every close is a Merkle root anchored on-chain.", "ব্যাংক দিন শেষে হিসাব মেলায়। এখন কার্বন বাজারও: প্রতিটি ক্লোজ অন-চেইনে নোঙর করা মার্কল রুট।"),
    "pp_title": ("Tonne Passport", "টন পাসপোর্ট"),
    "pp_sub": ("A shareable, QR-verifiable certificate for any credit range.", "যেকোনো ক্রেডিট রেঞ্জের জন্য শেয়ারযোগ্য, QR-যাচাইযোগ্য সনদ।"),
    "case_title": ("Auditor case files", "অডিটর কেস ফাইল"),
    "case_sub": ("One click: timeline, evidence rows, rule triggered, blocking tx hash and Merkle proof.", "এক ক্লিকে: সময়রেখা, প্রমাণ, ট্রিগার হওয়া নিয়ম, আটকানো tx হ্যাশ ও মার্কল প্রমাণ।"),
}


def lang() -> str:
    return st.session_state.get("lang", "en")


def t(key: str) -> str:
    en, bn = S.get(key, (key, key))
    return bn if lang() == "bn" else en


def language_selector() -> None:
    st.sidebar.radio(t("lang"), ["en", "bn"], format_func=lambda x: "English" if x == "en" else "বাংলা", key="lang", horizontal=True)
