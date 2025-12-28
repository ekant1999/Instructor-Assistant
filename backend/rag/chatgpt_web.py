import asyncio
import os
import json
import subprocess
from typing import List, Optional

from playwright.async_api import async_playwright, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError


class ChatGPTWebLLM:
    """Wrapper for ChatGPT web interface using Playwright automation."""

    def __init__(self, headless: bool = True, timeout: int = 60000):
        """Initialize ChatGPT Web LLM wrapper.

        Args:
            headless: Run browser in headless mode (default: True)
            timeout: Timeout in milliseconds for operations (default: 60000)
        """
        self.headless = headless
        self.timeout = timeout
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self._initialized = False

    async def _initialize(self):
        """Initialize Playwright browser and navigate to ChatGPT. Handles login detection and waits for user login if needed."""
        if self._initialized:
            return

        self.playwright = await async_playwright().start()

        user_data_dir = os.path.expanduser("~/.chatgpt-browser")
        os.makedirs(user_data_dir, exist_ok=True)

        singleton_lock = os.path.join(user_data_dir, "SingletonLock")
        if os.path.exists(singleton_lock):
            try:
                os.remove(singleton_lock)
            except:
                pass

        try:
            result = subprocess.run(
                ['pgrep', '-f', f'.*{user_data_dir}.*'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            os.kill(int(pid), 9)
                        except:
                            pass
        except:
            pass

        try:
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir,
                headless=self.headless,
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                args=['--disable-blink-features=AutomationControlled']
            )
        except Exception as e:
            error_msg = str(e)
            if "ProcessSingleton" in error_msg or "SingletonLock" in error_msg:
                try:
                    if os.path.exists(singleton_lock):
                        os.remove(singleton_lock)
                    await asyncio.sleep(2)
                    subprocess.run(['pkill', '-f', 'chromium.*chatgpt-browser'], capture_output=True)
                    await asyncio.sleep(2)
                    self.context = await self.playwright.chromium.launch_persistent_context(
                        user_data_dir,
                        headless=self.headless,
                        viewport={'width': 1280, 'height': 720},
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        args=['--disable-blink-features=AutomationControlled']
                    )
                except Exception as e2:
                    raise ValueError(
                        f"Failed to start browser. Another instance may be running. "
                        f"Please close any existing browser windows and try again. Error: {str(e2)}"
                    )
            else:
                raise

        if len(self.context.pages) > 0:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()

        try:
            await self.page.goto('https://chat.openai.com', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            login_indicators = [
                self.page.locator('text=Log in').first,
                self.page.locator('button:has-text("Log in")').first,
                self.page.locator('a[href*="login"]').first
            ]

            needs_login = False
            for indicator in login_indicators:
                if await indicator.count() > 0:
                    try:
                        if await indicator.is_visible(timeout=2000):
                            needs_login = True
                            break
                    except:
                        pass

            if needs_login:
                if not self.headless:
                    print("\n" + "="*60)
                    print("⚠️  ChatGPT requires login")
                    print("="*60)
                    print("Please log in to ChatGPT in the browser window that opened.")
                    print("The system will wait for you to complete login...")
                    print("="*60 + "\n")

                    max_wait = 300
                    waited = 0
                    while waited < max_wait:
                        await asyncio.sleep(2)
                        waited += 2

                        chat_input = self.page.locator('textarea[placeholder*="Message"], textarea[id*="prompt"]').first
                        if await chat_input.count() > 0:
                            try:
                                await chat_input.wait_for(state='visible', timeout=5000)
                                print("✓ Login detected! Continuing...")
                                break
                            except:
                                pass
                    else:
                        raise ValueError(
                            "Login timeout. Please ensure you're logged into ChatGPT.\n"
                            "Tip: Run with headless=False to see the browser and login manually."
                        )
                else:
                    raise ValueError(
                        "ChatGPT requires login. Please:\n"
                        "1. Set headless=False in the code to see the browser\n"
                        "2. Or manually log in to ChatGPT in a browser first\n"
                        "3. The persistent context will save your session\n"
                        "4. Restart the application after logging in once"
                    )

            self._initialized = True
        except PlaywrightTimeoutError:
            raise ValueError("Failed to load ChatGPT. Please check your internet connection.")

    async def _send_message(self, message: str) -> str:
        """Send a message to ChatGPT and wait for response. Handles finding input field, entering text, submitting, and extracting response."""
        if not self._initialized:
            await self._initialize()

        try:
            if self.page is None or self.page.is_closed():
                self._initialized = False
                await self._initialize()
            else:
                try:
                    _ = self.page.url
                except:
                    self._initialized = False
                    await self._initialize()

            # Navigate to ChatGPT if not already there
            try:
                if 'chat.openai.com' not in self.page.url:
                    await self.page.goto('https://chat.openai.com', wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(3)
            except:
                self._initialized = False
                await self._initialize()
                await self.page.goto('https://chat.openai.com', wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)

            await self.page.wait_for_timeout(2000)
            loading_selectors = ['button[aria-label*="Stop"]', 'div[class*="loading"]', 'div[class*="typing"]']
            for loading_sel in loading_selectors:
                try:
                    loading_el = await self.page.query_selector(loading_sel)
                    if loading_el:
                        for _ in range(15):
                            await self.page.wait_for_timeout(2000)
                            loading_el = await self.page.query_selector(loading_sel)
                            if not loading_el:
                                break
                        break
                except:
                    pass

            await asyncio.sleep(2)

            try:
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1)
            except:
                pass

            textarea_selectors = [
                'div[contenteditable="true"]',
                'div[contenteditable][role="textbox"]',
                'textarea[placeholder*="Message"]',
                'textarea[id*="prompt"]',
                'textarea',
            ]

            textarea = None
            for selector in textarea_selectors:
                try:
                    textarea = self.page.locator(selector).first
                    if await textarea.count() > 0:
                        await textarea.wait_for(state='visible', timeout=5000)
                        if await textarea.is_visible():
                            is_enabled = await textarea.is_enabled()
                            if is_enabled or 'contenteditable' in selector:
                                break
                except:
                    textarea = None
                    continue

            if textarea is None:
                try:
                    all_inputs = await self.page.query_selector_all('div[contenteditable], textarea, input[type="text"]')
                    if len(all_inputs) > 0:
                        for inp in reversed(all_inputs[-5:]):
                            try:
                                is_visible = await self.page.evaluate('(el) => el.offsetParent !== null && (el.offsetWidth > 0 || el.offsetHeight > 0)', inp)
                                if is_visible:
                                    element_selector = await self.page.evaluate('''(el) => {
                                        if (el.contentEditable === "true") return 'div[contenteditable="true"]';
                                        if (el.tagName === 'TEXTAREA') return 'textarea';
                                        if (el.tagName === 'INPUT') return 'input[type="text"]';
                                        return null;
                                    }''', inp)
                                    if element_selector:
                                        textarea = self.page.locator(element_selector).last
                                        break
                            except:
                                continue
                except:
                    pass

            if textarea is None:
                raise ValueError("Could not find ChatGPT input field. The page structure may have changed.")

            try:
                tag_name = await textarea.evaluate('el => el.tagName.toLowerCase()')
                is_contenteditable = tag_name == 'div' or await textarea.evaluate('el => el.contentEditable === "true"')
            except:
                is_contenteditable = 'contenteditable' in textarea_selectors[0]

            await textarea.click()
            await asyncio.sleep(0.5)

            if is_contenteditable:
                await textarea.evaluate('el => { el.focus(); el.innerText = ""; el.textContent = ""; }')
                await asyncio.sleep(0.3)
                escaped_message = json.dumps(message)
                await textarea.evaluate(f'el => {{ el.focus(); const text = {escaped_message}; el.innerText = text; el.textContent = text; el.dispatchEvent(new Event("input", {{ bubbles: true }})); el.dispatchEvent(new Event("change", {{ bubbles: true }})); }}')
                await asyncio.sleep(0.5)
            else:
                await textarea.fill('')
                await asyncio.sleep(0.3)
                await textarea.fill(message)
                await asyncio.sleep(0.5)

            try:
                initial_message_count = await self.page.evaluate('''() => {
                    const messages = Array.from(document.querySelectorAll('div[data-message-author-role="assistant"]'));
                    return messages.length;
                }''')
            except:
                initial_message_count = 0

            try:
                await textarea.press('Enter')
                await asyncio.sleep(2)
            except:
                try:
                    send_button = self.page.locator('button[data-testid*="send"], button:has-text("Send"), button[aria-label*="Send"]').first
                    if await send_button.count() > 0 and await send_button.is_visible():
                        await send_button.click()
                        await asyncio.sleep(2)
                    else:
                        await textarea.press('Enter')
                        await asyncio.sleep(2)
                except:
                    raise ValueError("Failed to send message to ChatGPT")

            await self.page.wait_for_timeout(3000)

            response_selectors = [
                'div[data-message-author-role="assistant"]',
                'div[class*="markdown"]',
                'div[class*="message"]',
                'div[class*="AssistantMessage"]',
                'div[role="assistant"]',
            ]

            loading_selectors = ['button[aria-label*="Stop"]', 'div[class*="loading"]', 'div[class*="typing"]']
            max_wait = 90
            waited = 0
            response_found = False

            while waited < max_wait:
                current_message_count = await self.page.evaluate('''() => {
                    const messages = Array.from(document.querySelectorAll('div[data-message-author-role="assistant"]'));
                    return messages.length;
                }''')

                for selector in response_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        if len(elements) > initial_message_count:
                            last_element = elements[-1]
                            text = await self.page.evaluate('(el) => el.innerText', last_element)
                            if text and text.strip() and len(text.strip()) > 10:
                                await asyncio.sleep(3)
                                is_loading = False
                                for loading_sel in loading_selectors:
                                    if await self.page.query_selector(loading_sel):
                                        is_loading = True
                                        break
                                if not is_loading:
                                    response_found = True
                                    break
                    except:
                        continue

                if response_found:
                    break

                await asyncio.sleep(2)
                waited += 2

            for selector in response_selectors:
                try:
                    assistant_messages = self.page.locator(selector)
                    count = await assistant_messages.count()
                    if count > initial_message_count:
                        last_message = assistant_messages.last
                        response_text = await last_message.inner_text()
                        if response_text and response_text.strip() and len(response_text.strip()) > 10:
                            await asyncio.sleep(2)
                            response_text = await last_message.inner_text()
                            if response_text and response_text.strip():
                                return response_text.strip()
                except:
                    continue

            page_text = await self.page.evaluate(f'''(initialCount) => {{
                const selectors = [
                    'div[data-message-author-role="assistant"]',
                    'div[class*="markdown"]',
                    'div[class*="message"]',
                    'div[class*="AssistantMessage"]',
                    'div[role="assistant"]',
                ];

                let messages = [];
                for (const selector of selectors) {{
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > initialCount) {{
                        messages = Array.from(elements);
                        break;
                    }}
                }}

                if (messages.length > initialCount) {{
                    const lastMessage = messages[messages.length - 1];
                    return lastMessage.innerText || '';
                }}

                return '';
            }}''', initial_message_count)

            if page_text and page_text.strip() and len(page_text.strip()) > 10:
                return page_text.strip()

            raise ValueError("No response received from ChatGPT. The page structure may have changed.")

        except PlaywrightTimeoutError:
            raise ValueError(f"ChatGPT response timeout after {self.timeout}ms. The model might be slow or the page structure changed.")
        except (BrokenPipeError, OSError) as e:
            if isinstance(e, OSError) and e.errno == 32:
                # Broken pipe - reset connection
                self._initialized = False
                self.context = None
                self.page = None
                raise ValueError(
                    "Connection lost with ChatGPT web app. Please try again. "
                    "If the error persists, make sure you're logged into ChatGPT."
                )
            raise ValueError(f"Connection error with ChatGPT: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            if "Broken pipe" in error_msg or "Errno 32" in error_msg:
                # Reset connection
                self._initialized = False
                self.context = None
                self.page = None
                raise ValueError(
                    "Connection lost with ChatGPT web app. Please try again. "
                    "If the error persists, make sure you're logged into ChatGPT."
                )
            raise ValueError(f"Error communicating with ChatGPT: {str(e)}")

    def invoke(self, messages: List) -> str:
        """Synchronous interface for LangChain. Formats messages and sends to ChatGPT, handling async execution."""
        prompt = self._format_messages(messages)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._run_in_thread, prompt)
                    return future.result()
            else:
                return loop.run_until_complete(self._send_message(prompt))
        except (RuntimeError, BrokenPipeError, OSError) as e:
            # Handle broken pipe and event loop errors
            if isinstance(e, BrokenPipeError) or (isinstance(e, OSError) and e.errno == 32):
                # Reset initialization to force reconnection
                self._initialized = False
                if self.context:
                    try:
                        # Try to close context in a new loop
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        new_loop.run_until_complete(self.close())
                        new_loop.close()
                    except:
                        pass
                self.context = None
                self.page = None

                # Retry once with a fresh connection
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(self._send_message(prompt))
                except Exception as retry_error:
                    raise ValueError(
                        f"Connection error with ChatGPT web app. Please try again. "
                        f"If the error persists, make sure you're logged into ChatGPT. "
                        f"Error: {str(retry_error)}"
                    )
            else:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(self._send_message(prompt))
        except Exception as e:
            error_msg = str(e)
            if "Broken pipe" in error_msg or "Errno 32" in error_msg:
                # Reset and retry
                self._initialized = False
                self.context = None
                self.page = None
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(self._send_message(prompt))
                except Exception as retry_error:
                    raise ValueError(
                        f"Connection error with ChatGPT web app. Please try again. "
                        f"If the error persists, make sure you're logged into ChatGPT. "
                        f"Error: {str(retry_error)}"
                    )
            raise

    def _run_in_thread(self, prompt: str) -> str:
        """Run async message sending in a new event loop within a thread (for nested async contexts)."""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(self._send_message(prompt))
        except (BrokenPipeError, OSError) as e:
            if isinstance(e, OSError) and e.errno == 32:
                # Broken pipe - reset and retry
                self._initialized = False
                self.context = None
                self.page = None
                # Retry in the same loop
                return new_loop.run_until_complete(self._send_message(prompt))
            raise
        finally:
            try:
                # Give pending tasks time to complete
                pending = asyncio.all_tasks(new_loop)
                if pending:
                    new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except:
                pass
            try:
                new_loop.close()
            except:
                pass

    def _format_messages(self, messages: List) -> str:
        """Format LangChain message objects (SystemMessage, HumanMessage) into a single prompt string for ChatGPT."""
        system_content = None
        user_content = None

        for msg in messages:
            if hasattr(msg, 'content'):
                content = msg.content
            elif isinstance(msg, dict):
                content = msg.get('content', str(msg))
            else:
                content = str(msg)

            if hasattr(msg, '__class__'):
                class_name = msg.__class__.__name__
                if 'System' in class_name:
                    system_content = content
                elif 'Human' in class_name:
                    if user_content is None:
                        user_content = content
                    else:
                        user_content += "\n\n" + content
                else:
                    if user_content is None:
                        user_content = content
                    else:
                        user_content += "\n\n" + content
            else:
                if user_content is None:
                    user_content = content
                else:
                    user_content += "\n\n" + content

        if system_content and user_content:
            return f"{system_content}\n\n{user_content}"
        elif user_content:
            return user_content
        elif system_content:
            return system_content
        else:
            formatted_parts = []
            for msg in messages:
                if hasattr(msg, 'content'):
                    formatted_parts.append(msg.content)
                elif isinstance(msg, dict):
                    formatted_parts.append(msg.get('content', str(msg)))
                else:
                    formatted_parts.append(str(msg))
            return "\n\n".join(formatted_parts)

    async def close(self):
        """Close browser context and cleanup Playwright resources."""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        self._initialized = False
        self.context = None
        self.page = None

