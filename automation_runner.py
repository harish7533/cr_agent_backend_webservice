import logging

from playwright.sync_api import sync_playwright
from new_project_creation.backend.automation_run_manager import RunManager

logger = logging.getLogger()

# 🔴 Always keep base URL clean (NO trailing slash)
BASE_URL = "https://design.instanda.com"

def run():
    # =========================================================
    # 🚀 INIT RUN MANAGER
    # =========================================================
    run = RunManager()
    run.setup()

    logger = run.get_logger()

    policyNumber = None
    payment_done = False

    with sync_playwright() as p:

        # 🚀 Launch browser
        browser = p.chromium.launch(
            headless=False,  # headless=False → shows UI (good for learning/debugging)
            slow_mo=100, # slow_mo=100 → slows actions so we can see steps clearly
            # args=["--disable-dev-shm-usage", "--disable-gpu", "--no-sandbox"]
            )

        # 🧠 Context = browser session (cookies, auth, etc.)
        context = browser.new_context()

        # 📄 Open a new tab
        page = context.new_page()

        # =========================================================
        # 🔐 STEP 1 — LOGIN
        # =========================================================
        try:
            page.goto(BASE_URL, timeout=30000)
        except Exception as e:
            print("Navigation warning:", e)

        # Fill login form
        page.fill("input[name='UserName']", "HarishALE")
        page.fill("input[name='Password']", "ALE$@2026Instanda")
        page.click("input[type='submit']")

        # Wait until network is stable (important after login)
        page.wait_for_load_state("networkidle")

        logger.info("✅ Logged in successfully")

        # =========================================================
        # ☁️ STEP 2 — OPEN PUBLISH DROPDOWN
        # =========================================================

        # Click cloud icon (dropdown trigger)
        page.click("a.messages-link.dropdown-toggle")

        # Wait until dropdown is visible (avoid timing issues)
        dropdown = page.locator("ul.dropdown-menu.dropdown-messages")
        dropdown.wait_for(state="visible")

        logger.info("✅ Publish dropdown opened")

        # =========================================================
        # 🔘 STEP 3 — SELECT 'TEST' RADIO BUTTON
        # =========================================================

        # Ensures correct environment (Test / Live / UAT)
        page.check("#publishTest")

        # Safety check (very important in automation)
        assert page.is_checked("#publishTest"), "❌ Test radio not selected!"

        logger.info("✅ Test environment selected")

        # =========================================================
        # 🔗 STEP 4 — GET PUBLISH LINK (SAFE WAY)
        # =========================================================

        # Extract relative URL dynamically (avoids hardcoding)
        relative_href = page.get_attribute(
            "a[data-action='publist-test']",
            "href"
        )

        if not relative_href:
            raise Exception("❌ Publish link not found!")

        logger.info(f"Relative URL: {relative_href}")

        # =========================================================
        # 🚀 STEP 5 — TRIGGER PUBLISH
        # =========================================================

        # ⚠️ Better to CLICK UI (instead of goto) to simulate real user
        page.click("a[data-action='publist-test']")

        # Wait for publish page
        page.wait_for_load_state("networkidle")

        logger.info("✅ Publish page opened")

        # Select publish type
        page.check("input[name='PublishType'][value='QuickPublish']")

        # Submit publish
        page.click("input[type='submit']")

        # Wait for publish to complete
        page.wait_for_load_state("networkidle")

        logger.info("✅ Publish triggered successfully")

        # =========================================================
        # 🆕 STEP 6 — HANDLE NEW TAB (VERY IMPORTANT)
        # =========================================================

        # Wait for new tab BEFORE clicking
        with context.expect_page() as new_page_info:
            page.click("#ViewTestButton")  # ✅ FIXED selector

        # Switch to new tab
        new_page = new_page_info.value

        # Wait for new tab to fully load
        new_page.wait_for_load_state("networkidle")

        logger.info(f"✅ Switched to new tab: {new_page.url}")

        # Close old tab (optional but clean)
        page.close()

        state = run.smart_wait(new_page, logger) # 🔥 SMART WAIT instead of networkidle

        # =========================================================
        # 🔐 STEP 7 — LOGIN AGAIN (NEW TAB)
        # =========================================================

        new_page.fill("input[name='UserName']", "HarishALE")
        new_page.fill("input[name='Password']", "ALE$@2026Instanda")

        new_page.click("button[type='submit']")
        new_page.wait_for_load_state("networkidle")

        logger.info("✅ Logged into Agent portal")

        # =========================================================
        # 🔎 STEP 8 — NAVIGATE TO SEARCH PAGE
        # =========================================================

        try:
            new_page.click("a[href='/Public/AgentRetrieveQuoteCrossPackage']")
            new_page.wait_for_load_state("networkidle")
        except Exception as e:
            print("Error occurred while navigating to search page:", e)

        logger.info("✅ Navigated to search page")

        # =========================================================
        # 🔍 STEP 9 — SEARCH FOR QUOTE
        # =========================================================

        # new_page.fill(
        #     "input[name='QuoteSearchParams[5].ParameterValueId']",
        #     "TSTMP0018680"
        # )

        new_page.fill(
            "input[id='26926']",
            "TSTTL0020179" #TSTTL0020167, TSTTL0020171
        )

        new_page.click("#agentSearchButton")

        # =========================================================
        # 📊 STEP 10 — WAIT FOR TABLE (IMPORTANT: dynamic content)
        # =========================================================

        new_page.wait_for_selector(
            "#agentSearchResultsTable",
            state="visible"
        )

        # Target latest transaction row
        row = new_page.locator(
            "#agentSearchResultsTable tr.latest-transaction"
        )
        row.wait_for(state="visible")

        logger.info("✅ Latest transaction row found")

        # =========================================================
        # 🔗 STEP 11 — CLICK 'VIEW'
        # =========================================================

        view_link = row.locator("a:has-text('View')")
        view_link.click()

        logger.info("✅ Clicked 'View'")

        new_page.wait_for_load_state("networkidle")

        # =========================================================
        # 📸 STEP 12 — TAKE SCREENSHOT
        # =========================================================

        screenshot_file = run.get_screenshot_path("latest_transaction.png")
        new_page.screenshot(path=screenshot_file)
        logger.info(f"📸 Screenshot saved: {screenshot_file}")

        # =========================================================
        # 🔁 STEP 13 — COPY / RE-QUOTE
        # =========================================================

        new_page.click(".btnCopyReQuote:has-text('Copy/re-quote')")
        logger.info("✅ Copy/Re-quote clicked")

        # =========================================================
        # 🔁 STEP — HANDLE MULTI-PAGE FLOW (Continue Button Loop)
        # =========================================================

        while True:
            # ⏳ Wait for page reload (IMPORTANT)
            # new_page.wait_for_load_state("networkidle")

            current_url = new_page.url

            # 📊 Extract details
            page_number, created_from_type, page_name = run.extract_page_details(current_url)

            # 🧾 Log details
            logger.info(f"PageName: {page_name} | PageNumber: {page_number} | CreatedFromType: {created_from_type}")
            logger.info(f"URL: {current_url}")
            # =====================================================
            # 🎯 STEP — CAPTURE POLICY NUMBER (ONLY ON CONFIRMATION)
            # =====================================================

            if (
                "PublicBoltPayments/ConfirmBillingDetails" in current_url
                and not payment_done
            ):
                run.handle_payment(new_page, logger)
                payment_done = True
                continue  # Skip to next iteration after payment

            # 🛑 Stop condition
            if page_name.lower() == "confirmation2":
                logger.info("🎯 Reached confirmation page. Stopping loop.")
                
                try:
                    # 🔍 Wait for the policy number element
                    policy_locator = new_page.locator(
                        "span.policy-number span.number-area"
                    )

                    policy_locator.wait_for(state="visible", timeout=10000)

                    # 📥 Extract text
                    policyNumber = policy_locator.inner_text().strip()

                    if policyNumber:
                        logger.info(f"✅ Policy Number Captured: {policyNumber}")
                         # 🔥 FINALIZE RUN (RENAME FOLDER)
                        run.finalize(policyNumber)
                         # 🔁 Refresh logger after finalize
                        logger = run.get_logger()

                except Exception as e:
                    logger.error(f"❌ Failed to capture policy number: {str(e)}")

                # =====================================================
                # 🚀 REDIRECT TO DASHBOARD
                # =====================================================
                try:
                    logger.info("➡️ Redirecting to Agent Dashboard...")

                    new_page.goto(f"{BASE_URL}/Public/AgentDashboard")

                    # wait for page to load properly
                    new_page.wait_for_load_state("networkidle")

                    logger.info(f"✅ Redirected to: {new_page.url}")

                except Exception as e:
                    logger.error(f"❌ Redirect failed: {str(e)}")

                break  # 🛑 EXIT LOOP

            # =====================================================
            # 🔘 STEP — CLICK CONTINUE BUTTON
            # =====================================================

            try:
            # 🔍 Find Continue button (robust selector)
                continue_button = new_page.locator(
                    "button[name='continueButton'], input[type='submit']"
                )

                if continue_button.count() > 0:
                    btn = continue_button.first

                    btn.wait_for(state="visible", timeout=10000)

                    # 🔥 ensure it's clickable
                    btn.scroll_into_view_if_needed()
                    new_page.wait_for_timeout(500)

                    btn.click()
                    logger.info("➡️ Clicked Continue button")

                else:
                    logger.warning("⚠️ Continue button not present on this page")

            except Exception as e:
                logger.info(f"❌ Continue button not found: {str(e)}")\
            
            # ❗ DO NOT break here anymore
            # let loop continue to detect next state

            if state == "dialog":
                # Handle dialog-specific logic if needed
                try:
                    new_page.click('.btn.btn-block.btn-primary.mt-1')
                    logger.info("✅ Dialog confirmed")
                except:
                    pass

            # Small safety wait (helps flaky UI)
            new_page.wait_for_timeout(6000)

        # =========================================================
        # 🧹 FINAL STEP — CLEANUP
        # =========================================================

        new_page.close()
        context.close()
        browser.close()

        logger.info("🎉 ALL STEPS COMPLETED SUCCESSFULLY")
        
# ▶️ Run script
run()