import os
import time
import shutil
import logging
import threading

from datetime import datetime
from urllib.parse import urlparse, parse_qs

class RunManager:
    def __init__(self, base_dir="testing_policy_cases"):
        self.base_dir = base_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.base_path = None
        self.screenshots_path = None
        self.log_file = None
        self.logger = None

        self._lock = threading.Lock()  # 🔒 Thread safety

    # =========================================================
    # 🚀 SETUP
    # =========================================================
    def setup(self):
        with self._lock:
            folder_name = f"temp_{self.timestamp}"
            self.base_path = os.path.join(self.base_dir, folder_name)

            self.screenshots_path = os.path.join(self.base_path, "screenshots")
            os.makedirs(self.screenshots_path, exist_ok=True)

            self.log_file = os.path.join(self.base_path, "automation.log")

            logging.basicConfig(
                filename=self.log_file,
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s",
                encoding="utf-8",
                force=True
            )

            self.logger = logging.getLogger()
            self.logger.info(f"📁 Temp run folder created: {self.base_path}")

    # =========================================================
    # 🔄 FINALIZE (RENAME FOLDER SAFELY)
    # =========================================================
    def finalize(self, policy_number):
        with self._lock:
            old_path = self.base_path
            new_folder_name = f"{policy_number}_{self.timestamp}"
            new_path = os.path.join(self.base_dir, new_folder_name)

            try:
                self.logger.info(f"📁 Renaming folder: {old_path} → {new_path}")

                # 🔥 FULLY release logging (fix WinError 5)
                logging.shutdown()

                # 🔁 Retry move (robust on Windows)
                for attempt in range(5):
                    try:
                        shutil.move(old_path, new_path)
                        break
                    except PermissionError:
                        time.sleep(1)
                else:
                    print(f"❌ Failed to rename after retries: {old_path}")
                    return False

                # 🔥 Reinitialize logging in new location
                self.log_file = os.path.join(new_path, "automation.log")

                logging.basicConfig(
                    filename=self.log_file,
                    level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    encoding="utf-8",
                    force=True
                )

                self.logger = logging.getLogger()
                self.logger.info(f"✅ Folder renamed to: {new_path}")

                # ✅ Update paths
                self.base_path = new_path
                self.screenshots_path = os.path.join(new_path, "screenshots")

                return True

            except Exception as e:
                print(f"❌ Rename error: {str(e)}")
                return False

    # =========================================================
    # 📸 HELPER: SAVE SCREENSHOT PATH
    # =========================================================
    def get_screenshot_path(self, filename):
        return os.path.join(self.screenshots_path, filename)

    # =========================================================
    # 🧾 GET LOGGER (SAFE ACCESS)
    # =========================================================
    def get_logger(self):
        return self.logger

    # =========================================================
    # 📁 GET CURRENT PATHS
    # =========================================================
    def get_paths(self):
        return {
            "base_path": self.base_path,
            "screenshots_path": self.screenshots_path,
            "log_file": self.log_file
        }
    def extract_page_details(self, url):
        parsed = urlparse(url)

        # 🔹 Extract query params
        query = parse_qs(parsed.query)

        page_number = query.get("pageNumber", ["N/A"])[0]
        created_from_type = query.get("createdFromType", ["N/A"])[0]

        # 🔹 Extract page name from path
        # Example: /Public/QuickQuoteQuestions
        path_parts = parsed.path.split("/")
        page_name = path_parts[2] if len(path_parts) > 2 else "Unknown"

        return page_number, created_from_type, page_name

    def handle_payment(self, page, logger):
        logger.info("💳 Payment page detected - entering card details")

        page.wait_for_load_state("domcontentloaded")
        iframe = page.frame_locator("iframe")

        iframe.locator("#cardNumber").wait_for(state="visible", timeout=15000)

        logger.info("✅ Card field detected inside iframe")

        # 🔥 Use TYPE instead of fill
        iframe.locator("#cardNumber").click()
        iframe.locator("#cardNumber").type("4242424242424242", delay=50)

        iframe.locator("#expiryDate").click()
        iframe.locator("#expiryDate").type("1227", delay=50)

        iframe.locator("#cvc").click()
        iframe.locator("#cvc").type("345", delay=50)

        logger.info("✅ Card details entered")

        # 🔥 Trigger validation
        page.mouse.click(10, 10)
        page.wait_for_timeout(1500)

        # 🔥 Wait for tooltip to disappear
        try:
            page.locator('[role="tooltip"]').wait_for(state="hidden", timeout=5000)
        except:
            pass

        # ✅ Click Next
        next_btn = iframe.get_by_role("button", name="Next").first
        next_btn.click()

        logger.info("➡️ Clicked Next")

        # ✅ Process payment (outside iframe)
        process_btn = iframe.get_by_role("button", name="Process payment")
        process_btn.wait_for(state="visible", timeout=20000)
        process_btn.click()

        logger.info("✅ Payment confirmed")

        page.wait_for_timeout(6000)
        logger.info(f"📄 Redirected to: {page.url}")

    def smart_wait(self, page, logger):
        try:
            # Try normal navigation first
            page.wait_for_load_state("domcontentloaded", timeout=5000)
            logger.info("📄 Page loaded")
            return "page"

        except TimeoutError:
            # If no navigation → check dialog
            if page.locator('.btn.btn-block.btn-primary.mt-1').is_visible():
                logger.info("📦 Dialog detected")
                return "dialog"

            logger.info("⚠️ Unknown state")
            return "unknown"
