"""
Telegram Web Crawler using Playwright

This script crawls messages from Telegram channels via web.telegram.org
No API credentials needed - just login with your phone number.

Usage:
    1. First login and save session:
       python -m crawler.web_crawler login

    2. Then crawl a channel by username:
       python -m crawler.web_crawler crawl <channel_username>

    3. Or crawl a private channel (no username) manually:
       python -m crawler.web_crawler crawl-manual

    4. Crawl with scrolling (last N hours or days):
       python -m crawler.web_crawler crawl-manual --hours 1
       python -m crawler.web_crawler crawl-manual --days 7
"""

import asyncio
import json
import sqlite3
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Page, Browser


class TelegramWebCrawler:
    """Crawler for Telegram channels via web interface"""

    def __init__(self, session_dir: str = None, db_path: str = None):
        """
        Initialize the crawler

        Args:
            session_dir: Directory to store browser session/state
            db_path: Path to SQLite database file
        """
        # Get project root directory (parent of crawler directory)
        PROJECT_ROOT = Path(__file__).parent.parent
        CRAWLER_DIR = Path(__file__).parent

        if session_dir is None:
            # Store session in crawler directory
            session_dir = str(CRAWLER_DIR / "telegram_web_session")
        if db_path is None:
            # Use shared database in database directory
            db_path = str(PROJECT_ROOT / "database" / "telegram_data.db")
            # Ensure database directory exists
            Path(PROJECT_ROOT / "database").mkdir(exist_ok=True)

        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        self.output_dir = PROJECT_ROOT / "crawled_data"
        self.output_dir.mkdir(exist_ok=True)
        self.db_path = db_path
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create channels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                peer_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name)
            )
        """)

        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                channel_id INTEGER,
                channel_name TEXT,
                text TEXT,
                timestamp INTEGER,
                date TEXT,
                time_display TEXT,
                views TEXT,
                has_photo BOOLEAN DEFAULT 0,
                has_video BOOLEAN DEFAULT 0,
                has_document BOOLEAN DEFAULT 0,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels(id),
                UNIQUE(message_id, channel_name)
            )
        """)

        # Create index for faster queries
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_name)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date)")

        conn.commit()
        conn.close()

    def save_to_database(self, messages: list[dict], channel_name: str) -> int:
        """
        Save messages to SQLite database

        Args:
            messages: List of message dictionaries
            channel_name: Name of the channel

        Returns:
            Number of new messages inserted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert or get channel
        cursor.execute(
            "INSERT OR IGNORE INTO channels (name) VALUES (?)",
            (channel_name,)
        )
        cursor.execute("SELECT id FROM channels WHERE name = ?",
                       (channel_name,))
        channel_id = cursor.fetchone()[0]

        # Insert messages
        inserted = 0
        for msg in messages:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO messages (
                        message_id, channel_id, channel_name, text, timestamp,
                        date, time_display, views, has_photo, has_video,
                        has_document, crawled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    msg.get("message_id"),
                    channel_id,
                    channel_name,
                    msg.get("text"),
                    msg.get("timestamp"),
                    msg.get("date"),
                    msg.get("time_display"),
                    msg.get("views"),
                    1 if msg.get("has_photo") else 0,
                    1 if msg.get("has_video") else 0,
                    1 if msg.get("has_document") else 0,
                    msg.get("crawled_at", datetime.now().isoformat())
                ))
                if cursor.rowcount > 0:
                    inserted += 1
            except Exception as e:
                print(f"Error inserting message {msg.get('message_id')}: {e}")
                continue

        conn.commit()
        conn.close()

        print(
            f"\n✓ Saved {inserted} new messages to database ({self.db_path})")
        print(f"  (Skipped {len(messages) - inserted} duplicates)")

        return inserted

    def get_messages(self, channel_name: str = None, limit: int = None) -> list[dict]:
        """
        Retrieve messages from database

        Args:
            channel_name: Filter by channel name (optional)
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM messages"
        params = []

        if channel_name:
            query += " WHERE channel_name = ?"
            params.append(channel_name)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_stats(self) -> dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM channels")
        total_channels = cursor.fetchone()[0]

        cursor.execute("""
            SELECT channel_name, COUNT(*) as count
            FROM messages
            GROUP BY channel_name
            ORDER BY count DESC
        """)
        channels = cursor.fetchall()

        conn.close()

        return {
            "total_messages": total_messages,
            "total_channels": total_channels,
            "channels": [{"name": c[0], "message_count": c[1]} for c in channels]
        }

    def get_existing_message_ids(self, channel_name: str) -> set:
        """
        Get all existing message IDs for a channel from database

        Args:
            channel_name: Name of the channel

        Returns:
            Set of message IDs that already exist in database
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT message_id FROM messages WHERE channel_name = ?",
            (channel_name,)
        )
        ids = {row[0] for row in cursor.fetchall()}

        conn.close()
        return ids

    def get_latest_message_timestamp(self, channel_name: str) -> Optional[int]:
        """
        Get the timestamp of the latest message for a channel

        Args:
            channel_name: Name of the channel

        Returns:
            Unix timestamp of latest message or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT MAX(timestamp) FROM messages WHERE channel_name = ?",
            (channel_name,)
        )
        result = cursor.fetchone()[0]

        conn.close()
        return result

    async def login(self):
        """
        Login to Telegram Web and save session for future use.
        This will open a browser window where you can login manually.
        """
        print("=" * 60)
        print("Telegram Web Login")
        print("=" * 60)
        print("\nA browser window will open. Please:")
        print("1. Enter your phone number")
        print("2. Enter the verification code from Telegram")
        print("3. Wait for the chat list to load")
        print("4. Press Enter in this terminal when done\n")

        async with async_playwright() as p:
            # Launch browser with persistent context to save session
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=False,  # Need visible browser for login
                viewport={"width": 1280, "height": 900},
                locale="en-US"
            )

            page = browser.pages[0] if browser.pages else await browser.new_page()

            # Set no timeout for login - user will manually indicate when done
            page.set_default_timeout(0)
            page.set_default_navigation_timeout(0)

            # Navigate to Telegram Web
            print("Opening Telegram Web...")
            await page.goto("https://web.telegram.org/k/")

            # Wait for user to login
            print("\n" + "=" * 60)
            print("Please login in the browser window.")
            print("After you see your chat list, press Enter here...")
            print("=" * 60)
            input()

            # User confirmed login - save session
            print("\n✓ Login successful! Session saved.")
            print(f"Session stored in: {self.session_dir}")
            print("\nYou can now crawl channels with:")
            print("  python -m crawler.web_crawler crawl <channel_username>")

            await browser.close()

    async def crawl_manual(
        self,
        output_name: str = "private_channel",
        hours: int = 0,
        scroll_delay: float = 1.0
    ) -> tuple[list[dict], str]:
        """
        Crawl a private channel by manually navigating to it.
        Opens browser, you navigate to the channel, press Enter to extract.

        Args:
            output_name: Name to use for the output file
            hours: Number of hours to scroll back (0 = no scrolling, just visible messages)
            scroll_delay: Delay between scrolls in seconds

        Returns:
            Tuple of (list of message dictionaries, channel name)
        """
        print("=" * 60)
        print("Manual Channel Crawl (for private channels without username)")
        print("=" * 60)
        print("\nA browser window will open. Please:")
        print("1. Click on the channel you want to crawl from your chat list")
        print("2. Wait for messages to load")
        print("3. Press Enter in this terminal to start extraction")
        if hours > 0:
            print(f"\nWill scroll back {hours} hour(s) to collect messages.\n")

        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=False,  # Need visible browser
                viewport={"width": 1280, "height": 900},
                locale="en-US"
            )

            page = browser.pages[0] if browser.pages else await browser.new_page()

            # Set no timeout
            page.set_default_timeout(0)
            page.set_default_navigation_timeout(0)

            # Navigate to Telegram Web
            print("Opening Telegram Web...")
            await page.goto("https://web.telegram.org/k/")

            # Wait for user to navigate to channel
            print("\n" + "=" * 60)
            print("Navigate to the channel you want to crawl.")
            print("Press Enter here when the channel messages are visible...")
            print("=" * 60)
            input()

            # Try to get channel name from the page
            channel_name = output_name
            try:
                # Try to get channel title from header
                title_elem = page.locator(
                    ".chat-info .peer-title, .top .peer-title")
                if await title_elem.count() > 0:
                    channel_name = await title_elem.first.inner_text()
                    print(f"Detected channel: {channel_name}")
            except:
                pass

            # Get existing message IDs for diff-based extraction
            existing_ids = self.get_existing_message_ids(channel_name)
            print(f"\nFound {len(existing_ids)} existing messages in database")

            # Scroll and extract messages
            if hours > 0:
                print(
                    f"Scrolling back {hours} hour(s) (will stop at existing messages)...")
                messages = await self._scroll_and_extract(
                    page, channel_name, hours, scroll_delay
                )
            else:
                print("Extracting visible messages...")
                all_messages = await self._extract_messages_with_timestamp(page, channel_name)
                # Filter to only new messages
                messages = [m for m in all_messages if m.get(
                    "message_id") not in existing_ids]
                skipped = len(all_messages) - len(messages)
                if skipped > 0:
                    print(f"Skipped {skipped} existing messages")

            print(f"\n✓ Found {len(messages)} NEW messages")

            await browser.close()
            return messages, channel_name

    async def _scroll_and_extract(
        self,
        page: Page,
        channel_name: str,
        hours: int,
        scroll_delay: float = 1.5
    ) -> list[dict]:
        """
        Scroll up to load older messages until reaching the cutoff time.
        Uses diff-based approach: stops when encountering messages already in database.

        Args:
            page: Playwright page
            channel_name: Channel name for message metadata
            hours: Number of hours to go back
            scroll_delay: Delay between scrolls

        Returns:
            List of NEW messages only (not in database)
        """
        cutoff_timestamp = (datetime.now() - timedelta(hours=hours)).timestamp()
        print(
            f"Cutoff time: {datetime.fromtimestamp(cutoff_timestamp).strftime('%Y-%m-%d %H:%M')}")

        # Load existing message IDs from database for diff-based crawling
        existing_ids = self.get_existing_message_ids(channel_name)
        print(
            f"Found {len(existing_ids)} existing messages in database for this channel")

        session_message_ids = set()  # Messages seen in this session
        new_messages = []  # Only NEW messages (not in DB)
        scroll_count = 0
        reached_cutoff = False
        reached_existing = False
        no_new_messages_count = 0
        consecutive_existing_count = 0

        while not reached_cutoff and not reached_existing:
            scroll_count += 1

            # Extract current messages with timestamps from data-timestamp attribute
            current_messages = await self._extract_messages_with_timestamp(page, channel_name)

            # Track new messages
            new_count = 0
            existing_count = 0
            oldest_timestamp = None

            for msg in current_messages:
                msg_id = msg.get("message_id")
                if not msg_id:
                    continue

                # Skip if already processed in this session
                if msg_id in session_message_ids:
                    continue

                session_message_ids.add(msg_id)

                # Check if message already exists in database
                if msg_id in existing_ids:
                    existing_count += 1
                    continue

                # This is a new message!
                new_messages.append(msg)
                new_count += 1

                # Track oldest message timestamp
                msg_ts = msg.get("timestamp")
                if msg_ts:
                    if oldest_timestamp is None or msg_ts < oldest_timestamp:
                        oldest_timestamp = msg_ts

                    # Check if we've reached the cutoff date
                    if msg_ts < cutoff_timestamp:
                        reached_cutoff = True

            oldest_str = datetime.fromtimestamp(oldest_timestamp).strftime(
                '%Y-%m-%d %H:%M') if oldest_timestamp else "?"
            print(
                f"Scroll {scroll_count}: +{new_count} new, {existing_count} existing, total new: {len(new_messages)}, oldest: {oldest_str}")

            if reached_cutoff:
                print(f"\n✓ Reached cutoff date!")
                break

            # If we found existing messages and no new ones, we've caught up
            if existing_count > 0 and new_count == 0:
                consecutive_existing_count += 1
                if consecutive_existing_count >= 2:
                    print(
                        f"\n✓ Reached existing messages in database. No more new messages to fetch.")
                    reached_existing = True
                    break
            else:
                consecutive_existing_count = 0

            # Check if we're getting any messages at all
            if new_count == 0 and existing_count == 0:
                no_new_messages_count += 1
                if no_new_messages_count >= 5:
                    print(
                        "\nNo messages after 5 scrolls. Reached beginning of channel.")
                    break
            else:
                no_new_messages_count = 0

            # Scroll up - target the correct scrollable container
            await page.evaluate("""
                () => {
                    const scrollable = document.querySelector('.bubbles .scrollable.scrollable-y');
                    if (scrollable) {
                        scrollable.scrollTop = 0;
                    }
                }
            """)

            # Wait for new messages to load
            await asyncio.sleep(scroll_delay)

        # Drop anything older than the cutoff (the message that triggered stop)
        new_messages = [
            m for m in new_messages
            if m.get("timestamp") is None or m.get("timestamp") >= cutoff_timestamp
        ]

        # Sort messages by timestamp (newest first)
        new_messages.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        return new_messages

    async def _extract_messages_with_timestamp(self, page: Page, channel_name: str) -> list[dict]:
        """Extract messages using data-timestamp attribute for accurate dates"""
        messages = []

        # Get all message bubbles with data-mid attribute
        bubbles = await page.locator(".bubble[data-mid]").all()

        for bubble in bubbles:
            try:
                msg_data = {
                    "channel": channel_name,
                    "crawled_at": datetime.now().isoformat(),
                }

                # Get message ID
                msg_id = await bubble.get_attribute("data-mid")
                if msg_id:
                    msg_data["message_id"] = msg_id

                # Get timestamp from data-timestamp attribute
                timestamp_str = await bubble.get_attribute("data-timestamp")
                if timestamp_str:
                    try:
                        timestamp = int(timestamp_str)
                        msg_data["timestamp"] = timestamp
                        msg_data["date"] = datetime.fromtimestamp(
                            timestamp).isoformat()
                    except:
                        pass

                # Get message text from .translatable-message
                text_elem = bubble.locator(".translatable-message")
                if await text_elem.count() > 0:
                    msg_data["text"] = await text_elem.first.inner_text()

                # Get full time display from title attribute
                time_elem = bubble.locator(".time-inner")
                if await time_elem.count() > 0:
                    title = await time_elem.first.get_attribute("title")
                    if title:
                        msg_data["time_display"] = title

                # Get views count
                views_elem = bubble.locator(".post-views")
                if await views_elem.count() > 0:
                    views_text = await views_elem.first.inner_text()
                    msg_data["views"] = views_text.strip()

                # Check for media
                if await bubble.locator(".media-photo, .photo").count() > 0:
                    msg_data["has_photo"] = True
                if await bubble.locator(".media-video, .video").count() > 0:
                    msg_data["has_video"] = True
                if await bubble.locator(".document").count() > 0:
                    msg_data["has_document"] = True

                # Only add if we have a message ID
                if msg_data.get("message_id"):
                    messages.append(msg_data)

            except Exception:
                continue

        return messages

    async def crawl_channel(
        self,
        channel_username: str,
        headless: bool = True,
        wait_time: int = 5
    ) -> list[dict]:
        """
        Crawl messages from a Telegram channel

        Args:
            channel_username: Channel username (without @)
            headless: Run browser in headless mode
            wait_time: Time to wait for messages to load (seconds)

        Returns:
            List of message dictionaries
        """
        channel_username = channel_username.replace(
            "@", "").replace("https://t.me/", "")

        print(f"\nCrawling channel: {channel_username}")
        print("-" * 50)

        async with async_playwright() as p:
            # Use saved session
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=headless,
                viewport={"width": 1280, "height": 900},
                locale="en-US"
            )

            page = browser.pages[0] if browser.pages else await browser.new_page()

            try:
                # Navigate directly to channel
                channel_url = f"https://web.telegram.org/k/#{channel_username}"
                print(f"Opening: {channel_url}")
                await page.goto(channel_url, wait_until="networkidle")

                # Wait for page to load
                print(f"Waiting {wait_time} seconds for content to load...")
                await asyncio.sleep(wait_time)

                # Check if we're logged in
                login_form = await page.locator(".input-wrapper").count()
                if login_form > 0:
                    chat_list = await page.locator(".chat-list").count()
                    if chat_list == 0:
                        print(
                            "\n✗ Not logged in! Please run 'python -m crawler.web_crawler login' first.")
                        await browser.close()
                        return []

                # Extract messages
                messages = await self._extract_messages(page, channel_username)

                print(f"\n✓ Extracted {len(messages)} messages")

                await browser.close()
                return messages

            except Exception as e:
                print(f"\n✗ Error crawling channel: {e}")
                await browser.close()
                raise

    async def _extract_messages(self, page: Page, channel_username: str) -> list[dict]:
        """Extract messages from the current page"""
        messages = []

        # Wait for message bubbles to appear
        try:
            await page.wait_for_selector(".bubble", timeout=10000)
        except:
            print("No messages found or timeout waiting for messages")
            return messages

        # Get all message bubbles
        bubbles = await page.locator(".bubble").all()
        print(f"Found {len(bubbles)} message elements")

        for i, bubble in enumerate(bubbles):
            try:
                msg_data = {
                    "index": i,
                    "channel": channel_username,
                    "crawled_at": datetime.now().isoformat(),
                }

                # Get message ID from data attribute
                msg_id = await bubble.get_attribute("data-mid")
                if msg_id:
                    msg_data["message_id"] = msg_id

                # Get message text
                text_elem = bubble.locator(".message, .text-content")
                if await text_elem.count() > 0:
                    msg_data["text"] = await text_elem.first.inner_text()

                # Get timestamp
                time_elem = bubble.locator(".time, .time-inner")
                if await time_elem.count() > 0:
                    time_text = await time_elem.first.inner_text()
                    msg_data["time"] = time_text.strip()

                # Get views count
                views_elem = bubble.locator(".post-views")
                if await views_elem.count() > 0:
                    views_text = await views_elem.first.inner_text()
                    msg_data["views"] = views_text.strip()

                # Check for media
                has_photo = await bubble.locator(".media-photo, .photo").count() > 0
                has_video = await bubble.locator(".media-video, .video").count() > 0
                has_document = await bubble.locator(".document").count() > 0

                if has_photo:
                    msg_data["has_photo"] = True
                if has_video:
                    msg_data["has_video"] = True
                if has_document:
                    msg_data["has_document"] = True

                # Only add if we got some content
                if msg_data.get("text") or msg_data.get("has_photo") or msg_data.get("has_video"):
                    messages.append(msg_data)

            except Exception as e:
                print(f"  Warning: Error extracting message {i}: {e}")
                continue

        return messages

    async def save_messages(
        self,
        messages: list[dict],
        channel_name: str,
        format: str = "json"
    ) -> Path:
        """
        Save messages to file

        Args:
            messages: List of message dictionaries
            channel_name: Name for the output file
            format: Output format ('json' or 'jsonl')

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in channel_name if c.isalnum()
                            or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')

        if format == "json":
            filename = self.output_dir / f"{safe_name}_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        elif format == "jsonl":
            filename = self.output_dir / f"{safe_name}_{timestamp}.jsonl"
            with open(filename, 'w', encoding='utf-8') as f:
                for msg in messages:
                    f.write(json.dumps(msg, ensure_ascii=False) + '\n')
        else:
            raise ValueError(f"Unsupported format: {format}")

        print(f"\nSaved {len(messages)} messages to {filename}")
        return filename


async def main():
    """Main function - CLI interface"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nCommands:")
        print("  login                      - Login to Telegram Web and save session")
        print("  crawl <channel_username>   - Crawl a channel by username (after login)")
        print(
            "  crawl-manual [output_name] - Crawl a private channel manually (no username needed)")
        print("  stats                      - Show database statistics")
        print("\nOptions:")
        print(
            "  --hours N                  - Scroll back N hours (default: 0 = visible only)")
        print(
            "  --days N                   - Scroll back N days (can combine with --hours)")
        print("  --visible                  - Show browser window (for crawl command)")
        print("\nExamples:")
        print("  python -m crawler.web_crawler login")
        print("  python -m crawler.web_crawler crawl durov")
        print("  python -m crawler.web_crawler crawl-manual")
        print("  python -m crawler.web_crawler crawl-manual --hours 1     # Last 1 hour")
        print("  python -m crawler.web_crawler crawl-manual --days 7      # Last 7 days")
        print("  python -m crawler.web_crawler crawl-manual --days 1 --hours 12")
        print("  python -m crawler.web_crawler stats")
        return

    command = sys.argv[1].lower()
    crawler = TelegramWebCrawler()

    # Parse --hours / --days lookback arguments
    hours = 0
    days = 0
    for i, arg in enumerate(sys.argv):
        if arg == "--hours" and i + 1 < len(sys.argv):
            try:
                hours = int(sys.argv[i + 1])
            except ValueError:
                print(
                    f"Error: --hours requires a number, got: {sys.argv[i + 1]}")
                return
        elif arg == "--days" and i + 1 < len(sys.argv):
            try:
                days = int(sys.argv[i + 1])
            except ValueError:
                print(
                    f"Error: --days requires a number, got: {sys.argv[i + 1]}")
                return

    lookback_hours = hours + (days * 24)

    if command == "login":
        await crawler.login()

    elif command == "crawl-manual":
        # Get optional output name (skip if it's a flag or number)
        output_name = "private_channel"
        for arg in sys.argv[2:]:
            if not arg.startswith("--") and not arg.isdigit():
                output_name = arg
                break

        result = await crawler.crawl_manual(output_name=output_name, hours=lookback_hours)
        messages, channel_name = result

        if messages:
            crawler.save_to_database(messages, channel_name)
            # Parse into trades so the dashboard/API can serve data immediately
            from api.parser import TradingMessageParser
            TradingMessageParser(crawler.db_path).parse_and_store_all()
        else:
            print("\nNo messages extracted.")
            print("Make sure you navigated to the channel before pressing Enter.")

    elif command == "crawl":
        if len(sys.argv) < 3:
            print("Error: Please provide a channel username")
            print("Usage: python -m crawler.web_crawler crawl <channel_username>")
            print("\nFor private channels without username, use:")
            print("  python -m crawler.web_crawler crawl-manual")
            return

        channel = sys.argv[2]

        # Parse optional arguments
        headless = "--visible" not in sys.argv

        messages = await crawler.crawl_channel(
            channel_username=channel,
            headless=headless
        )

        if messages:
            crawler.save_to_database(messages, channel)
            from api.parser import TradingMessageParser
            TradingMessageParser(crawler.db_path).parse_and_store_all()
        else:
            print("\nNo messages extracted. Try:")
            print("  1. Run with --visible flag to see what's happening:")
            print(f"     python -m crawler.web_crawler crawl {channel} --visible")
            print("  2. Make sure you're logged in: python -m crawler.web_crawler login")
            print(
                "  3. For private channels without username, use: python -m crawler.web_crawler crawl-manual")

    elif command == "stats":
        stats = crawler.get_stats()
        print("\n" + "=" * 50)
        print("Database Statistics")
        print("=" * 50)
        print(f"Total messages: {stats['total_messages']}")
        print(f"Total channels: {stats['total_channels']}")
        if stats['channels']:
            print("\nMessages per channel:")
            for ch in stats['channels']:
                print(f"  - {ch['name']}: {ch['message_count']} messages")
        print("=" * 50)

    else:
        print(f"Unknown command: {command}")
        print("Use 'login', 'crawl', 'crawl-manual', or 'stats'")


if __name__ == "__main__":
    asyncio.run(main())

