import csv
import json
import time
import os
import string

from bs4 import BeautifulSoup
import requests
from fake_headers import Headers
from selenium import webdriver


class Parser:
    """Represents a parser that collects film data from every page and saves it in .json or .csv format"""

    __base_url = 'https://www.kinopoisk.ru/lists/movies/top500/'

    def __init__(self):
        # self.page_counter = 1
        self.headers = Headers().generate()
        self.all_films = []
        self.parser_title = 'Some title'
        self.parser_desc = 'Some desc'

    def test_req(self, url: str, tries: int = 5) -> requests.Response:
        """Wrapper function on requests to manage bad requests"""
        try:
            response = requests.get(url, headers=self.headers)
            print(f'[+] {url} {response.status_code}')
        except Exception as e:
            time.sleep(3)
            if not tries:
                raise e
            print(f'[INFO] tries={tries} => {url}')
            return self.test_req(url, tries=tries-1)
        else:
            return response

    @staticmethod
    def print_error(exc: Exception, msg: str = '') -> None:
        print(f'[ERROR] {msg} => {exc}')

    @staticmethod
    def print_success(msg: str) -> None:
        print(f'[SUCCESS] {msg}')

    @staticmethod
    def print_msg(msg: str) -> None:
        print(f'[INFO] {msg}')

    def save_pages(self, from_page: int = 1, to_page: int = 2) -> None:
        """Saves pages into src/page_indx with selenium"""
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        CHROME_DRIVER_PATH = os.path.join(os.getcwd(), 'chromedriver', 'chromedriver.exe')
        options = webdriver.ChromeOptions()
        options.add_argument(f'user-agent={self.headers["User-Agent"]}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        service = Service(executable_path=CHROME_DRIVER_PATH)
        driver = webdriver.Chrome(options=options, service=service)

        for i in range(from_page, to_page):
            url = f'{self.__base_url}?page={i}'
            try:
                driver.get(url=url)

                try:
                    element_present = EC.presence_of_element_located((By.CSS_SELECTOR, 'div.styles_root__ti07r'))
                    WebDriverWait(driver, 5).until(element_present)
                except TimeoutException:
                    break

                with open(f'src/page_{i}.html', 'w', encoding='utf-8') as file:
                    file.write(driver.page_source)

            except Exception as exc:
                print(f'[ERROR] unable to get page source code {url} => {exc}')

        driver.quit()

    def parse_page_soup(self, soup: BeautifulSoup) -> list[dict]:
        """Parses current page and gets data about all films in it"""

        def get_film_link() -> str:
            try:
                return 'https://www.kinopoisk.ru/' + soup_film.select_one('a.base-movie-main-info_link__YwtP1')['href'].strip()
            except:
                return 'no link'

        def get_film_title() -> str:
            try:
                return soup_film.select_one(
                    'div.base-movie-main-info_mainInfo__ZL_u3 span'
                ).text.strip()
            except:
                return 'no link'

        def get_film_title_en() -> str:
            try:
                txt = soup_film.select_one(
                    'div.desktop-list-main-info_secondaryTitleSlot__mc0mI span.desktop-list-main-info_secondaryTitle__ighTt'
                ).text.strip()

                return ''.join( filter(lambda x: x in set(string.printable), txt) )

            except:
                return 'no eng title'

        def get_film_release_date() -> int:
            try:
                return int(soup_film.select_one(
                    'div.desktop-list-main-info_secondaryTitleSlot__mc0mI span.desktop-list-main-info_secondaryText__M_aus'
                ).text.strip(' ,').replace('\xa0', ' ').split(', ')[0])
            except:
                return 0

        def get_film_duration() -> int:
            try:
                return int(soup_film.select_one(
                    'div.desktop-list-main-info_secondaryTitleSlot__mc0mI span.desktop-list-main-info_secondaryText__M_aus'
                ).text.strip(' ,').replace('\xa0', ' ').split(', ')[1].replace('мин.', '').strip())
            except:
                return 0

        def get_film_country() -> str:
            try:
                return soup_film.select_one(
                    'div.desktop-list-main-info_additionalInfo__Hqzof span.desktop-list-main-info_truncatedText__IMQRP'
                ).text.strip().split(' ')[0]
            except:
                return 'no country'

        def get_film_genre() -> str:
            try:
                return soup_film.select_one(
                    'div.desktop-list-main-info_additionalInfo__Hqzof span'
                ).text.replace('\xa0', ' ').replace('•', '').split('Режиссёр')[0].strip().split(' ')[-1]
            except:
                return 'no genre'

        def get_film_director() -> str:
            try:
                return soup_film.select_one(
                    'div.desktop-list-main-info_additionalInfo__Hqzof span.desktop-list-main-info_truncatedText__IMQRP'
                ).text.strip().split('Режиссёр: ')[-1]
            except:
                return 'no director'

        def get_film_main_roles() -> str:
            try:
                return ''.join(
                    soup_film.select_one(
                    'div.desktop-list-main-info_additionalInfo__Hqzof'
                     ).find_next_sibling().span.text.strip().split('В ролях: ')[1:]
                )
            except:
                return 'no main roles'

        def get_film_rating() -> str:
            try:
                return soup_film.select_one(
                    'div.styles_user__2wZvH div.styles_kinopoiskValueBlock__qhRaI'
                ).text.strip().replace('.', ',')
            except:
                return 0

        def get_film_votes() -> int:
            try:
                return int(soup_film.select_one(
                    'div.styles_user__2wZvH span.styles_kinopoiskCount__2_VPQ'
                ).text.strip().replace(' ', ''))
            except:
                return 0

        soup_films = soup.select('div.styles_contentSlot__h_lSN main div.styles_root__ti07r')
        films_data = []

        for soup_film in soup_films:
            film_data = {}
            film_data['link'] = get_film_link()
            film_data['title'] = get_film_title()
            film_data['title_en'] = get_film_title_en()
            film_data['release_date'] = get_film_release_date()
            film_data['duration'] = get_film_duration()
            film_data['country'] = get_film_country()
            film_data['genre'] = get_film_genre()
            film_data['director'] = get_film_director()
            film_data['main_roles'] = get_film_main_roles()
            film_data['rating'] = get_film_rating()
            film_data['votes'] = get_film_votes()

            films_data.append(film_data)

        return films_data

    def parse_pages(self) -> None:
        """Collects all films together"""
        curr_dir = os.path.join(os.getcwd(), 'src')
        file_names = [f for f in os.listdir(curr_dir) if os.path.isfile(os.path.join(curr_dir, f))]

        def get_parser_info(soup: BeautifulSoup):
            content_section = soup.select_one('div.styles_contentSlot__h_lSN main')
            try:
                self.parser_title = content_section.select_one('h1.styles_title__jB8AZ').text
                self.parser_desc = content_section.select_one('p.styles_description__FEk94').text
            except Exception as exc:
                self.print_error(exc, 'unable to get parser title or desc', )

        for i, file_name in enumerate(file_names):
            try:
                with open(f'src/{file_name}', 'r', encoding='utf-8') as file:
                    soup = BeautifulSoup(file.read(), 'lxml')
                    if i == 0:
                        get_parser_info(soup)
                    self.all_films += self.parse_page_soup(soup)
            except Exception as e:
                self.print_error(e)

    def save_data(self, json_flag=True, csv_flag=True) -> None:
        """Saves data to .json and .csv files"""
        dt = time.strftime('%m_%d_%H_%M')

        if json_flag:
            with open(f'{dt}.json', 'w', encoding='utf-8') as file:
                json.dump(self.all_films, file, indent=2, ensure_ascii=False)

        if csv_flag:
            with open(f'{dt}.csv', 'w', encoding='cp1251', newline='') as file:
                writer = csv.writer(file, delimiter=';')

                writer.writerow(
                    ['Ссылка', 'Название',
                     'Название ин.', 'Дата выхода',
                     'Длительность', 'Страна',
                     'Жанр', 'Режиссёр',
                     'В главных ролях', 'Рейтинг'
                     'Кол-во оценок'])

                for film in self.all_films:
                    film: dict
                    writer.writerow(film.values())

    def parse(self) -> None:
        """Unites all functions in one"""
        self.save_pages(1, 100)
        self.print_success('Pages were saved')

        self.parse_pages()
        self.print_success('Pages were parsed')

        self.save_data()
        self.print_success('Data was saved')


def main():
    parser = Parser()
    parser.parse()


if __name__ == "__main__":
    main()
