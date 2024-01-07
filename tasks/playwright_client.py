import asyncio
from typing import Any
from playwright.async_api import async_playwright
from playwright._impl._api_structures import ProxySettings
from playwright._impl._errors import TargetClosedError

from data.config import logger, METAMASK
from data.settings import NUMBER_OF_ATTEMPTS


class PlaywrightClient:

    def __init__(self, twitter_account, proxy, ref_code, private_key) -> None:
        self.twitter_account = twitter_account
        self.proxy = ProxySettings(self.setup_proxy(proxy))
        self.ref_code = ref_code
        self.private_key = private_key

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
    
    @staticmethod
    async def click(page, xpath, timeout=30000):
        await page.wait_for_selector(xpath, timeout=timeout)
        await page.click(xpath)

    @staticmethod
    async def fill(page, xpath, text, timeout=30000):
        await page.wait_for_selector(xpath, timeout=timeout)
        await page.fill(xpath, text)

    async def start_metamask_login(self, browser):
        print('я тут')
        await asyncio.sleep(2)
        page = browser.pages[-1]
        xpath_selector = "xpath=/html/body/div[1]/div/div[2]/div/div/div/ul/li[1]/div/input"
        await asyncio.sleep(1)
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[1]/div/div[2]/div/div/div/ul/li[2]/button"
        print('я тут')
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[1]/div/div[2]/div/div/div/div/button[1]"
        print('я тут 4')
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/form/div[1]/label/input"
        await self.fill(page, xpath_selector, '@1DAD324392139110213dsf2e!')
        xpath_selector = "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/form/div[2]/label/input"
        await self.fill(page, xpath_selector, '@1DAD324392139110213dsf2e!')
        xpath_selector = "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/form/div[3]/label/input"
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/form/button"
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/button[1]"
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[2]/div/div/section/div[1]/div/div/label/input"
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[2]/div/div/section/div[2]/div/button[2]"
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/button"
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/button"
        await self.click(page, xpath_selector)
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[2]/div/div/section/div[1]/div/button/span"
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[1]/div/div[2]/div/button"
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[3]/div[3]/div/section/div[3]/button"
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[3]/div[3]/div/section/div[2]/div[2]/button"
        await self.click(page, xpath_selector)
        xpath_selector = "xpath=/html/body/div[3]/div[3]/div/section/div[2]/div/div[1]/div/input"
        await self.fill(page, xpath_selector, self.private_key)
        xpath_selector = "xpath=/html/body/div[3]/div[3]/div/section/div[2]/div/div[2]/button[2]"
        await self.click(page, xpath_selector)
        return True

    async def claim(self):
        async with async_playwright() as p:
            for num, _ in enumerate(range(NUMBER_OF_ATTEMPTS), start=1):
                logger.debug(f'{self.twitter_account} | Попытка {num}')
                try:
                    browser = await p.chromium.launch_persistent_context(
                        user_data_dir='',
                        headless=True, # отвечает за фоновый режим True - фон, False - нет
                        args=[
                            f"--disable-extensions-except={METAMASK}",
                            f"--load-extension={METAMASK}"
                            ],
                        proxy=self.proxy
                    )
                    
                    logger.info(f'{self.twitter_account} | начинаю вход в метамаск')
                    status = await self.start_metamask_login(browser=browser)
                    if status:
                        logger.info(f'{self.twitter_account} | успешно установил расширение вошел в кошелек')
                    else:
                        logger.error(f'{self.twitter_account} | не удалось войти в кошелек')
                        await browser.close()
                        continue
                    
                    logger.info(f'{self.twitter_account} | начинаю авторизироваться на well3.com')
                    page = browser.pages[-1]
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
                        await self.click(popup, xpath_selector)
                    except TargetClosedError:
                        pass
                        
                    logger.info(f'{self.twitter_account} | успешно авторизировался на well3.com')
                    
                
                    xpath_selector = "xpath=/html/body/div/div[1]/main/section[2]/div/div/div[3]/button"
                    button = await page.wait_for_selector(xpath_selector)
                    is_button_disabled = await button.is_disabled()
                    if not is_button_disabled:
                        await self.click(page, xpath_selector)
                        
                        xpath_selector = "xpath=/html/body/div/div[1]/main/div/div[2]/div[1]/div[3]/button"
                        await self.click(page, xpath_selector)
                        xpath_selector = "xpath=/html/body/div[2]/div/div/div[2]/div/div/div/div/div[1]/div[2]/div[2]/div[1]/button/div/div"
                        await self.click(page, xpath_selector)
                        await asyncio.sleep(1)
                        page = browser.pages[-1]
                        xpath_selector = "xpath=/html/body/div[1]/div/div/div/div[3]/div[2]/footer/button[2]"
                        await self.click(page, xpath_selector)

                        # Подключение кошелька
                        try:
                            await self.click(page, xpath_selector)
                        except TargetClosedError:
                            pass
                        
                        # Подпись
                        # Подключение
                        page = browser.pages[1]
                        try:
                            xpath_selector = "xpath=/html/body/div/div[1]/main/div/div[2]/div[1]/div[3]/button"
                            await self.click(page, xpath_selector)
                        except TargetClosedError:
                            pass
                        
                        changed_network = False
                        # Сигн
                        await asyncio.sleep(1)
                        page = browser.pages[-1]
                        try:
                            xpath_selector = "xpath=/html/body/div[1]/div/div/div/div[4]/footer/button[2]"
                            await page.wait_for_selector(xpath_selector, timeout=3000)
                            await page.click(xpath_selector)
                        except TargetClosedError:
                            pass
                        except:
                            try:
                                await asyncio.sleep(1)
                                page = browser.pages[-1]
                                xpath_selector = "xpath=/html/body/div[1]/div/div/div/div[2]/div/button[2]"
                                await self.click(page, xpath_selector)
                                await self.click(page, xpath_selector)
                            except TargetClosedError:
                                pass
                            changed_network = True
                            
                        if not changed_network:
                            # Cмена сети
                            page = browser.pages[1]
                            xpath_selector = "xpath=/html/body/div/div[1]/main/div/div[2]/div[1]/div[3]/button"
                            await self.click(page, xpath_selector)

                            # Подтверждение
                            await asyncio.sleep(1)
                            page = browser.pages[-1]
                            xpath_selector = "xpath=/html/body/div[1]/div/div/div/div[2]/div/button[2]"
                            await self.click(page, xpath_selector)
                            await self.click(page, xpath_selector)

                        try:
                            # Транза слева 
                            page = browser.pages[1]
                            xpath_selector = "xpath=/html/body/div/div[1]/main/div/div[2]/div[1]/div[3]/div[1]"
                            await self.click(page, xpath_selector)
                            await asyncio.sleep(2)
                            xpath_selector ="xpath=/html/body/div/div[1]/div[3]/div/div[2]/div"
                            await self.click(page, xpath_selector, timeout=3000)
                            
                            # Подверждение
                            await asyncio.sleep(2)
                            page = browser.pages[-1]
                            try:
                                xpath_selector = "xpath=/html/body/div[1]/div/div/div/div[3]/div[3]/footer/button[2]"
                                await self.click(page, xpath_selector, timeout=3000)
                            except TargetClosedError:
                                    pass
                            
                            # Возврат к мастеру
                            page = browser.pages[1]
                            xpath_selector = "xpath=/html/body/div/div[1]/div[3]/div[2]/div/div/button[1]"
                            await self.click(page, xpath_selector)
                            logger.success(f'{self.twitter_account} | Успешно сминтил нфт слева')
                        except:
                            # Транза справа
                            xpath_selector = "xpath=/html/body/div/div[1]/main/div/div[2]/div[1]/div[3]/div[2]"
                            await self.click(page, xpath_selector)
                            await asyncio.sleep(2)
                            xpath_selector ="xpath=/html/body/div/div[1]/div[3]/div/div[2]/div"
                            await self.click(page, xpath_selector, timeout=3000)

                            # Подверждение
                            await asyncio.sleep(2)
                            page = browser.pages[-1]
                            try:
                                xpath_selector = "xpath=/html/body/div[1]/div/div/div/div[3]/div[3]/footer/button[2]"
                                await self.click(page, xpath_selector, timeout=3000)
                            except TargetClosedError:
                                    pass
                            
                            logger.success(f'{self.twitter_account} | Успешно сминтил нфт справа')
                            return True
                        
                            # Возврат к мастеру
                            page = browser.pages[1]
                            xpath_selector = "xpath=/html/body/div/div[1]/div[3]/div[2]/div/div/button[1]"
                            await self.click(page, xpath_selector)

                        xpath_selector = "xpath=/html/body/div/div[1]/main/div/div[2]/div[1]/div[3]/div[2]"
                        await self.click(page, xpath_selector)
                        await asyncio.sleep(2)
                        xpath_selector ="xpath=/html/body/div/div[1]/div[3]/div/div[2]/div"
                        await self.click(page, xpath_selector, timeout=3000)

                        await asyncio.sleep(2)
                        page = browser.pages[-1]
                        try:
                            xpath_selector = "xpath=/html/body/div[1]/div/div/div/div[3]/div[3]/footer/button[2]"
                            await self.click(page, xpath_selector, timeout=3000)
                        except TargetClosedError:
                                pass
                        
                        logger.success(f'{self.twitter_account} | Успешно сминтил нфт справа')
                        await browser.close()
                        return True
                    
                        # Возврат к мастеру
                        page = browser.pages[1]
                        xpath_selector = "xpath=/html/body/div/div[1]/div[3]/div[2]/div/div/button[1]"
                        await self.click(page, xpath_selector)

                        await asyncio.sleep(150)
                        
                    else:
                        logger.warning(f'{self.twitter_account} | нету доступных для минта книжек у мастера')
                        await browser.close()
                        return True
                except Exception as err:
                    print(err)
                    continue