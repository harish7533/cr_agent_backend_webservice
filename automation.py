<<<<<<< HEAD
from playwright.sync_api import sync_playwright
from job_store import update_job
from automation_run_manager import RunManager

BASE_URL = "https://design.instanda."

def run_automation(job_id, form_data):
    run = RunManager()
    run.setup()

    logger = run.get_logger()

    # 🔥 Extract dynamic values from frontend
    domain = form_data.get("siteName")
    username = form_data.get("userName")
    password = form_data.get("userPassword")
    agent_name = form_data.get("agentName")
    agent_password = form_data.get("agentPassword")
    policy_number_input = form_data.get("policyNumber")

    try:
        update_job(job_id, {"progress": 5, "message": "Launching browser..."})

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=100)
            context = browser.new_context()
            page = context.new_page()

            # =========================================================
            # 🔐 LOGIN
            # =========================================================
            update_job(job_id, {"progress": 10, "message": "Logging into portal..."})

            DOMAIN_URL = f"{BASE_URL}{domain}"
            print(f"🌐 Navigating to: {DOMAIN_URL}")
            page.goto(DOMAIN_URL, timeout=30000)

            page.fill("input[name='UserName']", username)
            page.fill("input[name='Password']", password)
            page.click("input[type='submit']")
            page.wait_for_load_state("networkidle")

            logger.info("✅ Logged in to design studio...")

            # =========================================================
            # ☁️ OPEN PUBLISH
            # =========================================================
            update_job(job_id, {"progress": 20, "message": "Opening publish menu..."})

            page.click("a.messages-link.dropdown-toggle")
            dropdown = page.locator("ul.dropdown-menu.dropdown-messages")
            dropdown.wait_for(state="visible")

            page.check("#publishTest")

            # =========================================================
            # 🚀 PUBLISH
            # =========================================================
            update_job(job_id, {"progress": 30, "message": "Triggering publish..."})

            assert page.is_checked("#publishTest"), "❌ Test radio not selected!"

            # Extract relative URL dynamically (avoids hardcoding)
            relative_href = page.get_attribute(
                "a[data-action='publist-test']",
                "href"
            )

            if not relative_href:
                raise Exception("❌ Publish link not found!")

            logger.info(f"Relative URL: {relative_href}")

            page.click("a[data-action='publist-test']")
            page.wait_for_load_state("networkidle")

            page.check("input[name='PublishType'][value='QuickPublish']")
            page.click("input[type='submit']")
            page.wait_for_load_state("networkidle")

            logger.info("✅ Publish triggered successfully")

            # =========================================================
            # 🆕 NEW TAB
            # =========================================================
            update_job(job_id, {"progress": 40, "message": "Opening test app..."})

            with context.expect_page() as new_page_info:
                page.click("#ViewTestButton")

            new_page = new_page_info.value
            new_page.wait_for_load_state("networkidle")
            page.close()

            state = run.smart_wait(new_page, logger)

            # =========================================================
            # 🔐 AGENT LOGIN
            # =========================================================
            update_job(job_id, {"progress": 50, "message": "Logging into agent portal..."})

            new_page.fill("input[name='UserName']", agent_name)
            new_page.fill("input[name='Password']", agent_password)
            new_page.click("button[type='submit']")
            new_page.wait_for_load_state("networkidle")
            logger.info("✅ Logged into Agent portal")

            # =========================================================
            # 🔍 SEARCH POLICY (🔥 USING FRONTEND VALUE)
            # =========================================================
            update_job(job_id, {"progress": 60, "message": f"Searching policy {policy_number_input}..."})

            new_page.click("a[href='/Public/AgentRetrieveQuoteCrossPackage']")
            new_page.wait_for_load_state("networkidle")

            new_page.locator("input[id='26926']").click()
            new_page.locator("input[id='26926']").type(policy_number_input, delay=60)
            new_page.mouse.click(10, 10)  # click outside to trigger validation
            new_page.click("#agentSearchButton")

            new_page.wait_for_selector("#agentSearchResultsTable", state="visible")

            row = new_page.locator("#agentSearchResultsTable tr.latest-transaction")
            row.wait_for(state="visible")

            row.locator("a:has-text('View')").click()
            new_page.wait_for_load_state("networkidle")

            # =========================================================
            # 🔁 COPY / REQUOTE
            # =========================================================
            update_job(job_id, {"progress": 70, "message": "Starting copy/re-quote..."})

            new_page.click(".btnCopyReQuote:has-text('Copy/re-quote')")

            payment_done = False
            final_policy_number = None

            # =========================================================
            # 🔁 LOOP FLOW
            # =========================================================
            while True:
                current_url = new_page.url

                page_number, created_from_type, page_name = run.extract_page_details(current_url)

                logger.info(f"PageName: {page_name} | PageNumber: {page_number} | CreatedFromType: {created_from_type}")

                # 💳 PAYMENT STEP
                if "PublicBoltPayments/ConfirmBillingDetails" in current_url and not payment_done:
                    update_job(job_id, {"progress": 80, "message": "Processing payment..."})

                    run.handle_payment(new_page, logger)
                    payment_done = True
                    continue

                # 🎯 CONFIRMATION PAGE
                if page_name.lower() == "confirmation2":
                    logger.info("🎯 Reached confirmation page. Stopping loop.")
                    update_job(job_id, {"progress": 90, "message": "Finalizing policy..."})

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

                        new_page.goto(f"{DOMAIN_URL}/Public/AgentDashboard")

                        # wait for page to load properly
                        new_page.wait_for_load_state("networkidle")

                        logger.info(f"✅ Redirected to: {new_page.url}")

                    except Exception as e:
                        logger.error(f"❌ Redirect failed: {str(e)}")

                    break

                # ➡️ CONTINUE BUTTON
                try:
                    continue_button = new_page.locator("button[name='continueButton'], input[type='submit']")

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
                    logger.warning(f"Continue not found: {str(e)}")

                if state == "dialog":
                # Handle dialog-specific logic if needed
                    try:
                        new_page.click('.btn.btn-block.btn-primary.mt-1')
                        logger.info("✅ Dialog confirmed")
                    except:
                        pass

                new_page.wait_for_timeout(1000)  # minimal buffer (NOT sleep logic)

            # =========================================================
            # ✅ DONE
            # =========================================================
            update_job(job_id, {
                "status": "completed",
                "progress": 100,
                "message": f"Policy Created: {final_policy_number}"
            })

            new_page.close()
            context.close()
            browser.close()

    except Exception as e:
        logger.error(str(e))

        update_job(job_id, {
            "status": "failed",
            "message": str(e)
=======
from playwright.sync_api import sync_playwright
from backend.job_store import update_job
from backend.automation_run_manager import RunManager

BASE_URL = "https://design.instanda."

def run_automation(job_id, form_data):
    run = RunManager()
    run.setup()

    logger = run.get_logger()

    # 🔥 Extract dynamic values from frontend
    domain = form_data.get("siteName")
    username = form_data.get("userName")
    password = form_data.get("userPassword")
    agent_name = form_data.get("agentName")
    agent_password = form_data.get("agentPassword")
    policy_number_input = form_data.get("policyNumber")

    try:
        update_job(job_id, {"progress": 5, "message": "Launching browser..."})

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=100)
            context = browser.new_context()
            page = context.new_page()

            # =========================================================
            # 🔐 LOGIN
            # =========================================================
            update_job(job_id, {"progress": 10, "message": "Logging into portal..."})

            DOMAIN_URL = f"{BASE_URL}{domain}"
            print(f"🌐 Navigating to: {DOMAIN_URL}")
            page.goto(DOMAIN_URL, timeout=30000)

            page.fill("input[name='UserName']", username)
            page.fill("input[name='Password']", password)
            page.click("input[type='submit']")
            page.wait_for_load_state("networkidle")

            logger.info("✅ Logged in to design studio...")

            # =========================================================
            # ☁️ OPEN PUBLISH
            # =========================================================
            update_job(job_id, {"progress": 20, "message": "Opening publish menu..."})

            page.click("a.messages-link.dropdown-toggle")
            dropdown = page.locator("ul.dropdown-menu.dropdown-messages")
            dropdown.wait_for(state="visible")

            page.check("#publishTest")

            # =========================================================
            # 🚀 PUBLISH
            # =========================================================
            update_job(job_id, {"progress": 30, "message": "Triggering publish..."})

            assert page.is_checked("#publishTest"), "❌ Test radio not selected!"

            # Extract relative URL dynamically (avoids hardcoding)
            relative_href = page.get_attribute(
                "a[data-action='publist-test']",
                "href"
            )

            if not relative_href:
                raise Exception("❌ Publish link not found!")

            logger.info(f"Relative URL: {relative_href}")

            page.click("a[data-action='publist-test']")
            page.wait_for_load_state("networkidle")

            page.check("input[name='PublishType'][value='QuickPublish']")
            page.click("input[type='submit']")
            page.wait_for_load_state("networkidle")

            logger.info("✅ Publish triggered successfully")

            # =========================================================
            # 🆕 NEW TAB
            # =========================================================
            update_job(job_id, {"progress": 40, "message": "Opening test app..."})

            with context.expect_page() as new_page_info:
                page.click("#ViewTestButton")

            new_page = new_page_info.value
            new_page.wait_for_load_state("networkidle")
            page.close()

            state = run.smart_wait(new_page, logger)

            # =========================================================
            # 🔐 AGENT LOGIN
            # =========================================================
            update_job(job_id, {"progress": 50, "message": "Logging into agent portal..."})

            new_page.fill("input[name='UserName']", agent_name)
            new_page.fill("input[name='Password']", agent_password)
            new_page.click("button[type='submit']")
            new_page.wait_for_load_state("networkidle")
            logger.info("✅ Logged into Agent portal")

            # =========================================================
            # 🔍 SEARCH POLICY (🔥 USING FRONTEND VALUE)
            # =========================================================
            update_job(job_id, {"progress": 60, "message": f"Searching policy {policy_number_input}..."})

            new_page.click("a[href='/Public/AgentRetrieveQuoteCrossPackage']")
            new_page.wait_for_load_state("networkidle")

            new_page.locator("input[id='26926']").click()
            new_page.locator("input[id='26926']").type(policy_number_input, delay=60)
            new_page.mouse.click(10, 10)  # click outside to trigger validation
            new_page.click("#agentSearchButton")

            new_page.wait_for_selector("#agentSearchResultsTable", state="visible")

            row = new_page.locator("#agentSearchResultsTable tr.latest-transaction")
            row.wait_for(state="visible")

            row.locator("a:has-text('View')").click()
            new_page.wait_for_load_state("networkidle")

            # =========================================================
            # 🔁 COPY / REQUOTE
            # =========================================================
            update_job(job_id, {"progress": 70, "message": "Starting copy/re-quote..."})

            new_page.click(".btnCopyReQuote:has-text('Copy/re-quote')")

            payment_done = False
            final_policy_number = None

            # =========================================================
            # 🔁 LOOP FLOW
            # =========================================================
            while True:
                current_url = new_page.url

                page_number, created_from_type, page_name = run.extract_page_details(current_url)

                logger.info(f"PageName: {page_name} | PageNumber: {page_number} | CreatedFromType: {created_from_type}")

                # 💳 PAYMENT STEP
                if "PublicBoltPayments/ConfirmBillingDetails" in current_url and not payment_done:
                    update_job(job_id, {"progress": 80, "message": "Processing payment..."})

                    run.handle_payment(new_page, logger)
                    payment_done = True
                    continue

                # 🎯 CONFIRMATION PAGE
                if page_name.lower() == "confirmation2":
                    logger.info("🎯 Reached confirmation page. Stopping loop.")
                    update_job(job_id, {"progress": 90, "message": "Finalizing policy..."})

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

                        new_page.goto(f"{DOMAIN_URL}/Public/AgentDashboard")

                        # wait for page to load properly
                        new_page.wait_for_load_state("networkidle")

                        logger.info(f"✅ Redirected to: {new_page.url}")

                    except Exception as e:
                        logger.error(f"❌ Redirect failed: {str(e)}")

                    break

                # ➡️ CONTINUE BUTTON
                try:
                    continue_button = new_page.locator("button[name='continueButton'], input[type='submit']")

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
                    logger.warning(f"Continue not found: {str(e)}")

                if state == "dialog":
                # Handle dialog-specific logic if needed
                    try:
                        new_page.click('.btn.btn-block.btn-primary.mt-1')
                        logger.info("✅ Dialog confirmed")
                    except:
                        pass

                new_page.wait_for_timeout(1000)  # minimal buffer (NOT sleep logic)

            # =========================================================
            # ✅ DONE
            # =========================================================
            update_job(job_id, {
                "status": "completed",
                "progress": 100,
                "message": f"Policy Created: {final_policy_number}"
            })

            new_page.close()
            context.close()
            browser.close()

    except Exception as e:
        logger.error(str(e))

        update_job(job_id, {
            "status": "failed",
            "message": str(e)
>>>>>>> 0126ba55be4ed45c80e3526250e8f756142baddd
        })