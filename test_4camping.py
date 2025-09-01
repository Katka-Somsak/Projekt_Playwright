from playwright.sync_api import Page, sync_playwright
import pytest

#otevření prohlížeče
@pytest.fixture(params=["chromium", "webkit"])
def browser(request):
    with sync_playwright() as p:
        browser = getattr(p, request.param).launch(headless=False, slow_mo=1500)
        yield browser
        browser.close()

#otevření page
@pytest.fixture
def page(browser):
    page = browser.new_page()
    yield page
    page.close()


# přijetí nezbytných cookies, pokud se okno zobrazí
def refuse_cookies(page:Page):
    btn_set_cookies = page.locator("#cookieConsentModal > div > div > div.modal-footer > p > label")
    if btn_set_cookies.is_visible():
        btn_set_cookies.click()
        btn_accept_partial = page.locator("#savePartialSettings")
        btn_accept_partial.click()

# odmítnutí novinek, pokud se zobrazí
def refuse_news(page:Page):
    btn_refuse = page.locator("#onesignal-slidedown-cancel-button")
    if btn_refuse.is_visible():
        btn_refuse.click()

#spuštění stránky a odkliknutí cookies a novinek
def go_to_page(page:Page):
    page.goto("https://www.4camping.cz/")
    refuse_news(page)
    refuse_cookies(page)
    page.wait_for_timeout(2000)

# získání ceny produktu
def get_price(locator):
    price_string = locator.inner_text().replace("\xa0", "").replace("Kč", "").strip()
    price = int(price_string)
    return price

#1. test - Jsou po výběru v sekci boty -> Snežnice -> filtr podle značky opravdu všechny výsledky vyfiltrovány správně?
@pytest.mark.parametrize(
        "brand",
        ["MSR", "OAC", "Yate"]
)
def test_product_brand_filter(brand, page: Page):
    go_to_page(page)
    # sekce Boty
    shoe_category = page.locator("#categories > ul > li:nth-child(3) > a")
    shoe_category.hover()
    # výběr sekce Sněžnice
    snowshoes_btn = page.locator("#list_id_1030 > div:nth-child(3) > ul > li:nth-child(3) > a")
    snowshoes_btn.click()
    # rozkliknutí celé nabídky značek z bočního menu
    show_more_btn = page.locator("#parameters > section.js-category-filter-param.filter-param.filter-param--default.filter-producers.show-section > div > div > button")
    if show_more_btn.is_visible():
        show_more_btn.click()
    # nalezení konkrétní značky
    filter_brand = page.locator("#parameters > section.js-category-filter-param.filter-param.filter-param--default.filter-producers.show-section > div")
    brand_checkbox = filter_brand.get_by_label(brand)
    if not brand_checkbox.is_visible():
        pytest.skip(f"Značka {brand} se momentálně na eshopu v této kategorii neprodává.")
        
    brand_checkbox.click()
    # vytvoření seznamu značek ze zobrazených produktů
    brand_name = page.locator("#sect-catalog span.product-card__heading-producer")
    brand_name_list = brand_name.all()
    # kontrola názvu značky v každém řádku seznamu
    for i in brand_name_list:
        if i.is_visible():
            assert i.inner_text().strip() == brand


# 2.test - Zobrazuje se po přidání produktů do košíku správně spočítaná celková cena košíku?
@pytest.mark.parametrize(
        "ID_category_1, i_1, ID_category_2, i_2",
        [
            ("#categories > ul > li:nth-child(6) > a", "4", "#categories > ul > li:nth-child(2) > a", "8"),
            ("#categories > ul > li:nth-child(4) > a", "2", "#categories > ul > li:nth-child(8) > a", "12")
         ]
)
def test_cart_price(ID_category_1, i_1, ID_category_2, i_2, page: Page):
    go_to_page(page)
    # výber prvého produktu z nabídky, jeho cena a přidání do košíku
    category_1 = page.locator(ID_category_1)
    category_1.click()
    product_1 = page.locator(f"#sect-catalog > article:nth-child({i_1})")
    product_1.click()
    page.wait_for_timeout(2000)
    price_1 = get_price(page.locator("#priceSellingVat"))
    buy_btn_1 = page.locator("#sendToBasket")
    buy_btn_1.click()
    close_detail_1 = page.locator("#ajaxAddModal > div > div > button")
    close_detail_1.click()

    # výber druhého produktu z nabídky, jeho cena a přidání do košíku
    category_2 = page.locator(ID_category_2)
    category_2.click()
    product_2 = page.locator(f"#sect-catalog > article:nth-child({i_2})")
    product_2.click()
    page.wait_for_timeout(2000)
    price_2 = get_price(page.locator("#priceSellingVat"))
    buy_btn_2 = page.locator("#sendToBasket")
    buy_btn_2.click()
    close_detail_2 = page.locator("#ajaxAddModal > div > div > button")
    close_detail_2.click()

    # porovnání celkové ceny v košíku
    total_price = get_price(page.locator("#headerBasket > a > strong"))
    assert price_1 + price_2 == total_price


# 3. test - Jsou produkty seřazeny správně po vyhledání konkrétní značky, zobrazení všech nalezených produktů a seřazení dle ceny?
@pytest.mark.parametrize(
        "brand",
        ["Indiana Jerky", "Kari Traa", "MOOA"]
)
def test_sort_by_price(brand, page: Page):
    go_to_page(page)
    # vyhledání konkrétní značky
    search_product = page.locator("#search-desktop > form > div > div > div > input.text.search-query.form-field__input.lbx-input__desktop")
    search_product.fill(brand)
    search_product.press("Enter")

    # dále zobrazíme všechny produkty, ne jenom ty z první stránky (filtr může obsahovat produkty na jedné nebo více stránkách)
    more_pages_btn = page.locator("#results > div > div.results__footer-cell.results__footer-cell--mid > div > button")
    if more_pages_btn.is_visible():
        while more_pages_btn.is_visible():
            more_pages_btn.click()
   
    # najedeme na tlačítko "Nejlevnější" a seřadíme produkty vzestupně podle ceny
    sort_panel = page.locator("#categoryFilterSort")
    sort_cheapest_btn = sort_panel.locator("[data-sort-label='Nejlevnější']")
    sort_cheapest_btn.click()
    # projdeme všechny produkty, zjistíme jejich ceny a uložíme postupně do seznamu
    prices = page.locator("#sect-catalog span.card-price__full")
    product_count = prices.count()
    price_list = []

    for i in range(product_count):
        price = get_price(prices.nth(i))
        price_list.append(price)

    # ověříme, že ceny jsou správně seřazeny
    assert price_list == sorted(price_list)