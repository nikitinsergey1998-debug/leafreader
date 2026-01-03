# 📚 Book Reader — EPUB / FB2

A minimalist desktop e-book reader built with **Python** and **Qt (PySide6)**.
Focused on readability, stability, and a clean, distraction-free user experience.

---

## 🇷🇺 Описание проекта

**Leafreader** — это настольное приложение для чтения электронных книг в форматах **EPUB** и **FB2**.

Цель проекта — предоставить предсказуемый и надёжный инструмент для чтения без лишней сложности, тяжёлых интерфейсных слоёв и нестабильного поведения.

Приложение корректно работает с:

* HTML-контентом книг
* встроенными изображениями
* внутренними ресурсами
* большими книгами
* автоматическим восстановлением состояния между запусками

Проект делает акцент на качестве базового чтения, а не на перегруженности функциями.

---

## ✨ Возможности

* 📖 Поддержка форматов **EPUB** и **FB2**
* 📑 Навигация по главам (EPUB)
* 🗂️ Боковая панель с оглавлением
* 💾 Автоматическое сохранение состояния:

  * последняя открытая книга
  * текущая глава
  * позиция прокрутки
  * размер шрифта
* 🔍 Масштабирование текста
* 🖼️ Корректное отображение встроенных изображений
* 🗂️ Кэширование разобранного содержимого книг
* 🖥️ Полноэкранный режим
* ⌨️ Навигация с клавиатуры
* 🧩 Кроссплатформенная архитектура

---

## 🧠 Детали реализации

* собственный `QTextBrowser` с переопределённой загрузкой ресурсов
* пользовательские схемы ресурсов (`epub://`, `fb2://`)
* нормализация путей изображений внутри EPUB
* корректная обработка base64-изображений в FB2
* безопасное файловое кэширование с привязкой ко времени изменения файла
* автоматическое восстановление состояния при запуске
* отсутствие жёсткой зависимости от структуры книги

---

## 🛠️ Стек технологий

* **Python 3.9+**
* **PySide6 (Qt)**
* **ebooklib**
* **lxml**

---

## 🚀 Установка и запуск

```bash
git clone https://github.com/your-username/book-reader.git
cd book-reader
pip install -r requirements.txt
python main.py
```

---

## 📦 Зависимости

Установите зависимости командой:

```bash
pip install PySide6 ebooklib lxml pypdf
```

> Используйте виртуальное окружение для изоляции зависимостей.

---

## 📌 Статус проекта

Проект **стабилен и готов к использованию**.
Открыт для улучшений интерфейса, оптимизации отображения и расширения навигации.

---

# 📚 Book Reader — EPUB / FB2

A desktop application for reading **EPUB** and **FB2** e-books.
Designed to be predictable, reliable, and focused on core reading quality.

---

## 🇬🇧 Project Description

**Book Reader** is a desktop application for reading **EPUB** and **FB2** e-books.

The project aims to provide a predictable and reliable reading tool without unnecessary complexity, heavy UI layers, or unstable behavior.

It correctly handles:

* HTML-based book content
* embedded images
* internal resources
* large books
* automatic state restoration between launches

The application focuses on core reading quality rather than feature overload.

---

## ✨ Features

* 📖 Support for **EPUB** and **FB2**
* 📑 Chapter navigation (EPUB)
* 🗂️ Table of contents side panel
* 💾 Automatic reading state saving:

  * last opened book
  * current chapter
  * scroll position
  * font size
* 🔍 Text zoom control
* 🖼️ Embedded image rendering
* 🗂️ Parsed book content caching
* 🖥️ Fullscreen mode
* ⌨️ Keyboard navigation
* 🧩 Cross-platform architecture

---

## 🧠 Implementation Details

* custom `QTextBrowser` with overridden resource loading
* custom resource schemes (`epub://`, `fb2://`)
* normalized image paths inside EPUB content
* proper handling of base64 images in FB2
* safe file-based caching tied to file modification time
* automatic state restoration on startup
* no strict dependency on book structure

---

## 🛠️ Tech Stack

* **Python 3.9+**
* **PySide6 (Qt)**
* **ebooklib**
* **lxml**
