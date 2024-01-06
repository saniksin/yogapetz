import asyncio
from playwright.async_api import async_playwright
from playwright._impl._api_structures import ProxySettings
from playwright._impl._errors import TargetClosedError

from data.config import logger


class PlaywrightClient:

    def __init__(self, twitter_account, proxy, ref_code) -> None:
        self.twitter_account = twitter_account
        self.proxy = ProxySettings(self.setup_proxy(proxy))
        self.ref_code = ref_code

    def setup_proxy(self, proxy):
        username_password, server_port = proxy.replace('http://', '').split('@')
        username, password = username_password.split(':')
        server, port = server_port.split(':')
        proxy = {
            "server": f"http://{server}:{port}",
            "username": username,
            "password": password,
        }
        return proxy
        

    async def register(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir='',
                headless=False,
                # args=[
                #     f"--disable-extensions-except={METAMASK},{COOKIE_EDITOR}",
                #     f"--load-extension={METAMASK},{COOKIE_EDITOR}"],
                proxy=self.proxy
            )
            page = await browser.new_page()

            await page.goto("https://well3.com")
            xpath_selector = "xpath=/html/body/div/div[1]/main/div/section[2]/button"
            await page.wait_for_selector(xpath_selector)

            async with page.expect_popup() as popup_info:
                await page.click(xpath_selector)
            popup = await popup_info.value

            popup_context = popup.context
            await popup_context.add_cookies(
                [
                    {
                        "name": "auth_token",
                        "value": self.twitter_account.auth_token,
                        "domain": "api.twitter.com",
                        "path": "/",
                    },
                    {
                        "name": "ct0",
                        "value": self.twitter_account.ct0,
                        "domain": "api.twitter.com",
                        "path": "/",
                    },
                ]
            )

            try:
                xpath_selector = "xpath=/html/body/div[2]/div/form/fieldset/input[1]"
                await popup.wait_for_selector(xpath_selector)
                await popup.click(xpath_selector)
            except TargetClosedError:
                pass
                
            xpath_selector = "xpath=/html/body/div/div[1]/main/section/div/div/div/button"
            try:
                await page.wait_for_selector(xpath_selector, timeout=30000)
            except TimeoutError:
                logger.info(f'{self.twitter_account} | Уже зарегистрирован')
                await browser.close()
                return True
            await page.click(xpath_selector)
                        
            for num, letter in enumerate(self.ref_code, start=1):
                xpath_selector = f"xpath=/html/body/div/div[1]/main/section/div/div/div/div/div[{num}]/input"
                await page.wait_for_selector(xpath_selector)
                await page.fill(xpath_selector, letter)
                
            #/html/body/div/div[1]/main/section/div/div/div/button
                
            # Проверка наличия сообщения об ошибке
            error_selector = "xpath=/html/body/div/div[1]/main/section/div/div/div/div/div[6]"
            try:
                await page.wait_for_selector(error_selector, timeout=2000)
                logger.error(f'{self.twitter_account} | Не верный реф. код!')
                await browser.close()
                return False
            except TimeoutError:
                xpath_selector = f"xpath=/html/body/div/div[1]/main/section/div/div/div/button"
                await page.wait_for_selector(xpath_selector)
                await page.click(xpath_selector)

            await asyncio.sleep(150)

            await browser.close()
