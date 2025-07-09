# app.py
import streamlit as st
import openai
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import re
import json

# --- Konfigurasi Halaman ---
st.set_page_config(layout="centered", page_title="Book Summary Generator")

# --- Fungsi Reset Aplikasi ---
def reset_app():
    """Menghapus semua data dari session state untuk memulai dari awal."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]

# --- Inisialisasi Kunci API di Awal ---
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    SEARCH_ENGINE_ID = st.secrets["SEARCH_ENGINE_ID"]
except (FileNotFoundError, KeyError):
    if 'keys_loaded' not in st.session_state:
        st.error("Pastikan semua API Key (OpenAI, Google API, Search Engine ID) sudah diatur di st.secrets.")
    st.session_state.keys_loaded = False
else:
    st.session_state.keys_loaded = True

# --- FUNGSI-FUNGSI UTAMA ---
def get_book_cover_urls(title, author):
    search_url = "https://www.googleapis.com/customsearch/v1"
    query = f'"{title}" oleh {author} sampul buku resmi'
    params = {'q': query, 'key': GOOGLE_API_KEY, 'cx': SEARCH_ENGINE_ID, 'searchType': 'image', 'num': 4, 'imgSize': 'large', 'safe': 'high'}
    try:
        response = requests.get(search_url, params=params); response.raise_for_status()
        results = response.json()
        if 'items' in results: return [item['link'] for item in results['items']]
    except Exception as e: st.warning(f"Tidak dapat mengambil sampul buku: {e}")
    return []

def get_book_summary(title, author):
    prompt_text = f"""Analisis buku "{title}" oleh {author}. Identifikasi 6 pelajaran kunci atau ide utama dari buku tersebut. Untuk setiap pelajaran, berikan judul yang sangat singkat (2-4 kata) dan penjelasan dalam satu kalimat pendek. Format output sebagai daftar bernomor dengan format **Judul**: Penjelasan."""
    try:
        response = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": "Anda adalah asisten yang meringkas buku menjadi 6 poin kunci."}, {"role": "user", "content": prompt_text}])
        return response.choices[0].message.content
    except Exception as e: st.error(f"Terjadi kesalahan saat menghubungi OpenAI: {e}"); return None

def get_additional_details(title, author):
    prompt_text = f"""Untuk buku "{title}", cari di dalam basis pengetahuan Anda untuk informasi berikut dan sajikan dalam format objek JSON tunggal: 1. Sebuah kunci "retrieved_author" dengan nama penulis yang benar untuk buku ini. 2. Sebuah kunci "best_quote" dengan kutipan paling berkesan atau representatif dari buku tersebut. 3. Sebuah kunci "details" dengan objek sebagai nilainya, berisi kunci-kunci ini: "publisher", "publication_year", dan "page_count". Jika sebuah nilai tidak ditemukan, gunakan string "N/A". Contoh: {{"retrieved_author": "Osamu Dazai", "best_quote": "Sekarang aku tidak punya kebahagiaan maupun ketidakbahagiaan. Segalanya berlalu begitu saja.", "details": {{"publisher": "Gramedia Pustaka Utama", "publication_year": "2020", "page_count": "200"}}}}"""
    try:
        response = openai.chat.completions.create(model="gpt-4o-mini", response_format={"type": "json_object"}, messages=[{"role": "system", "content": "Anda adalah asisten peneliti yang menyediakan data buku akurat dalam format JSON."}, {"role": "user", "content": prompt_text}])
        return json.loads(response.choices[0].message.content)
    except Exception as e: st.warning(f"Tidak dapat mengambil detail tambahan: {e}"); return {"retrieved_author": author, "best_quote": "N/A", "details": {}}

# --- FUNGSI PARSING YANG DIPERBAIKI ---
def parse_summary_text(text):
    """Mengubah teks ringkasan menjadi daftar terstruktur dengan regex yang lebih fleksibel."""
    if not text: return []
    # Pola regex ini membuat tanda bintang (**) opsional, sehingga bisa menangani
    # format "1. **Judul**: Deskripsi" dan "1. Judul: Deskripsi".
    pattern = re.compile(r"^\d+\.\s+\*?(.*?)\*?:\s*(.*)", re.MULTILINE)
    matches = pattern.findall(text)
    # Membersihkan sisa tanda bintang dari judul jika ada
    return [{"title": match[0].replace('*', '').strip(), "description": match[1].strip()} for match in matches]

def create_infographic(book_title, author, themes, cover_url, additional_info):
    WIDTH, HEIGHT = 1200, 2200; BG_COLOR, ACCENT_COLOR = "#F4F6F6", "#4A90E2"; DARK_TEXT_COLOR, LIGHT_TEXT_COLOR, BODY_TEXT_COLOR = "#2C3E50", "#FFFFFF", "#34495E"; PADDING = 80
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR); draw = ImageDraw.Draw(img)
    try:
        font_main_title = ImageFont.truetype("Montserrat-Bold.ttf", 52); font_author = ImageFont.truetype("Montserrat-Regular.ttf", 30); font_theme_title = ImageFont.truetype("Montserrat-Bold.ttf", 24); font_desc = ImageFont.truetype("Montserrat-Regular.ttf", 18); font_number = ImageFont.truetype("Montserrat-Bold.ttf", 22); font_quote = ImageFont.truetype("Montserrat-Italic.ttf", 28); font_footer_title = ImageFont.truetype("Montserrat-Bold.ttf", 16); font_footer_text = ImageFont.truetype("Montserrat-Regular.ttf", 16)
    except IOError: font_main_title, font_author, font_theme_title, font_desc, font_number, font_quote, font_footer_title, font_footer_text = (ImageFont.load_default(),)*8
    HEADER_HEIGHT = 400; draw.rectangle([0, 0, WIDTH, HEADER_HEIGHT], fill=ACCENT_COLOR)
    if cover_url:
        try:
            cover_img_data = requests.get(cover_url).content; cover_img = Image.open(io.BytesIO(cover_img_data)); cover_size, cover_height = 280, int(280 * 1.5); cover_img = cover_img.resize((cover_size, cover_height)); img.paste(cover_img, (PADDING, (HEADER_HEIGHT - cover_height) // 2))
        except Exception: pass
    header_text_x = PADDING + 280 + 60; max_width_title = WIDTH - header_text_x - PADDING; words = book_title.upper().split(); lines, current_line = [], '';
    for word in words:
        if draw.textlength(current_line + word + ' ', font_main_title) <= max_width_title: current_line += word + ' '
        else: lines.append(current_line); current_line = word + ' '
    lines.append(current_line)
    current_y = 130
    for line in lines:
        if line.strip(): draw.text((header_text_x, current_y), line.strip(), font=font_main_title, fill=LIGHT_TEXT_COLOR); current_y += font_main_title.getbbox('A')[3] + 5
    draw.text((header_text_x, current_y + 10), f"Oleh {author}", font=font_author, fill=LIGHT_TEXT_COLOR)
    GAP, NUM_COLUMNS = 40, 2; COLUMN_WIDTH = (WIDTH - (2 * PADDING) - GAP) // NUM_COLUMNS; current_y_content = HEADER_HEIGHT + 60; last_box_y = 0
    for i, theme in enumerate(themes):
        col, row = i % NUM_COLUMNS, i // NUM_COLUMNS; box_x, box_y = PADDING + col * (COLUMN_WIDTH + GAP), current_y_content + row * (220 + GAP); last_box_y = box_y + 220
        draw.rounded_rectangle([box_x, box_y, box_x + COLUMN_WIDTH, box_y + 220], radius=15, fill="#FFFFFF"); circle_x, circle_y, circle_radius = box_x + 40, box_y + 40, 20
        draw.ellipse([circle_x - circle_radius, circle_y - circle_radius, circle_x + circle_radius, circle_y + circle_radius], fill=ACCENT_COLOR); draw.text((circle_x, circle_y), str(i + 1), font=font_number, fill=LIGHT_TEXT_COLOR, anchor="mm")
        text_start_x, text_max_width = circle_x + circle_radius + 20, COLUMN_WIDTH - 120; draw.text((text_start_x, circle_y), theme['title'], font=font_theme_title, fill=DARK_TEXT_COLOR, anchor="ls")
        desc_y = circle_y + 40; words_desc, line_desc = theme['description'].split(), '';
        for word in words_desc:
            if draw.textlength(line_desc + word + ' ', font_desc) <= text_max_width: line_desc += word + ' '
            else: draw.text((text_start_x, desc_y), line_desc, font=font_desc, fill=BODY_TEXT_COLOR); desc_y += font_desc.getbbox('A')[3] + 5; line_desc = word + ' '
        draw.text((text_start_x, desc_y), line_desc, font=font_desc, fill=BODY_TEXT_COLOR)
    quote_text = additional_info.get("best_quote", "");
    if quote_text and quote_text.lower() != "n/a":
        quote_y_start = last_box_y + 60; quote_padding = 40; quote_max_width = WIDTH - (2 * PADDING) - (2 * quote_padding)
        words_quote = quote_text.split(); lines_quote, current_line_quote = [], '';
        for word in words_quote:
            if draw.textlength(current_line_quote + word + ' ', font_quote) <= quote_max_width: current_line_quote += word + ' '
            else: lines_quote.append(current_line_quote); current_line_quote = word + ' '
        lines_quote.append(current_line_quote)
        line_height_quote = font_quote.getbbox('A')[3] + 8; quote_box_height = (len(lines_quote) * line_height_quote) + (2 * quote_padding)
        draw.rounded_rectangle([PADDING, quote_y_start, WIDTH - PADDING, quote_y_start + quote_box_height], radius=15, fill="#FFFFFF")
        quote_y = quote_y_start + quote_padding
        for line in lines_quote: draw.text((WIDTH / 2, quote_y), line.strip(), font=font_quote, fill=BODY_TEXT_COLOR, anchor="ma"); quote_y += line_height_quote
    footer_y = HEIGHT - 120; draw.line([PADDING, footer_y, WIDTH - PADDING, footer_y], fill="#DDDDDD", width=2)
    details = additional_info.get("details", {}); footer_items = {"PENERBIT": details.get("publisher", "N/A"), "TAHUN TERBIT": details.get("publication_year", "N/A"), "HALAMAN": str(details.get("page_count", "N/A"))}
    item_width = (WIDTH - 2 * PADDING) / len(footer_items)
    for i, (title, value) in enumerate(footer_items.items()): item_x = PADDING + i * item_width + item_width / 2; draw.text((item_x, footer_y + 35), title, font=font_footer_title, fill=ACCENT_COLOR, anchor="ms"); draw.text((item_x, footer_y + 60), value, font=font_footer_text, fill=BODY_TEXT_COLOR, anchor="ms")
    return img

# --- LOGIKA UTAMA APLIKASI ---
st.title("📚 Generator Infografis Ringkasan Buku")

if 'step' not in st.session_state:
    st.session_state.step = 1

# === LANGKAH 1: INPUT JUDUL & PENULIS ===
if st.session_state.step == 1:
    st.header("Langkah 1: Masukkan Detail Buku")
    if not st.session_state.get('keys_loaded', False): st.stop()
    with st.form("book_input_form"):
        book_title = st.text_input("Judul Buku", placeholder="Contoh: Gagal Menjadi Manusia")
        author_name = st.text_input("Nama Penulis", placeholder="Contoh: Osamu Dazai")
        submitted = st.form_submit_button("Cari & Validasi Buku →")
    if submitted and book_title and author_name:
        with st.spinner("Memvalidasi buku..."):
            info = get_additional_details(book_title, author_name)
            retrieved_author = info.get("retrieved_author", "").lower()
            user_author = author_name.lower()
            st.session_state.book_title = book_title
            st.session_state.user_author = author_name
            st.session_state.retrieved_author = info.get("retrieved_author", "N/A")
            st.session_state.additional_info = info
            if user_author in retrieved_author or retrieved_author in user_author:
                st.session_state.author_name = st.session_state.retrieved_author
                st.session_state.step = "processing"
            else:
                st.session_state.step = 1.5
        st.rerun()

# === LANGKAH 1.5: KONFIRMASI PENULIS ===
if st.session_state.step == 1.5:
    st.header("Langkah 1.5: Konfirmasi Penulis")
    st.warning(f"Penulis yang Anda masukkan (**{st.session_state.user_author}**) berbeda dengan yang kami temukan (**{st.session_state.retrieved_author}**).")
    st.write("Silakan pilih penulis yang benar untuk melanjutkan:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"Gunakan: {st.session_state.user_author}", use_container_width=True):
            st.session_state.author_name = st.session_state.user_author
            st.session_state.step = "processing"
            st.rerun()
    with col2:
        if st.button(f"Gunakan: {st.session_state.retrieved_author}", use_container_width=True):
            st.session_state.author_name = st.session_state.retrieved_author
            st.session_state.step = "processing"
            st.rerun()
    st.button("Kembali", on_click=reset_app)

# === LANGKAH ANTARA: PENGAMBILAN DATA ===
if st.session_state.step == "processing":
    with st.spinner("Mencari data lainnya..."):
        st.session_state.cover_urls = get_book_cover_urls(st.session_state.book_title, st.session_state.author_name)
        st.session_state.summary_text = get_book_summary(st.session_state.book_title, st.session_state.author_name)
    st.session_state.step = 2
    st.rerun()

# === LANGKAH 2: PEMILIHAN SAMPUL ===
if st.session_state.step == 2:
    st.header("Langkah 2: Pilih Sampul Buku")
    st.info(f"Menampilkan hasil untuk: **{st.session_state.book_title}** oleh **{st.session_state.author_name}**")
    if not st.session_state.cover_urls:
        st.error("Tidak ada gambar sampul yang ditemukan untuk buku ini."); st.button("Coba Lagi", on_click=reset_app)
    else:
        with st.form("cover_selection_form"):
            labels = [f"Gambar {i+1}" for i in range(len(st.session_state.cover_urls))]; cols = st.columns(len(st.session_state.cover_urls))
            for i, col in enumerate(cols):
                with col: st.image(st.session_state.cover_urls[i], use_container_width=True)
            chosen_index = st.radio("Pilihan Anda:", range(len(labels)), format_func=lambda x: labels[x], horizontal=True)
            submitted_cover = st.form_submit_button("Buat Infografis dengan Sampul Ini ✨")
            if submitted_cover:
                st.session_state.chosen_url = st.session_state.cover_urls[chosen_index]; st.session_state.step = 3; st.rerun()

# === LANGKAH 3: TAMPILKAN HASIL & AKSI (DENGAN DEBUG) ===
if st.session_state.step == 3:
    st.header("Langkah 3: Hasil Infografis Anda")
    
    with st.spinner("Membuat gambar akhir..."):
        # Cek apakah summary_text ada sebelum di-parse
        if not st.session_state.get("summary_text"):
            st.error("Teks ringkasan kosong. Terjadi masalah saat mengambil data dari AI.")
            st.button("Kembali ke Awal", on_click=reset_app)
        else:
            themes = parse_summary_text(st.session_state.summary_text)
            
            # Jika parsing gagal, tampilkan pesan error dan info debug
            if not themes:
                st.error("Gagal memproses teks ringkasan. Format respons dari AI tidak terduga.")
                st.info("Ini adalah teks mentah yang diterima dari AI:")
                st.text_area(
                    "Info Debug (Respons AI)", 
                    st.session_state.summary_text, 
                    height=300, 
                    disabled=True, 
                    label_visibility="collapsed"
                )
                st.button("Kembali ke Awal", on_click=reset_app)
            else:
                # Jika parsing berhasil, lanjutkan seperti biasa
                final_image = create_infographic(
                    st.session_state.book_title,
                    st.session_state.author_name,
                    themes,
                    st.session_state.chosen_url,
                    st.session_state.additional_info
                )
                
                st.success("Infografis berhasil dibuat!")
                st.image(final_image)
                
                buf = io.BytesIO()
                final_image.save(buf, format="PNG")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="⬇️ Download Gambar",
                        data=buf.getvalue(),
                        file_name=f"ringkasan_{st.session_state.book_title.replace(' ', '_').lower()}.png",
                        mime="image/png",
                        use_container_width=True
                    )
                with col2:
                    st.button("⬅️ Buat Ringkasan Baru", on_click=reset_app, use_container_width=True)
