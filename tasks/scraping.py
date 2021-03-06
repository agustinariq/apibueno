import requests
import os
import sys
import csv
from datetime import datetime
sys.path.insert(0, "./app/utils")

from wikipedia_table import parse_table

CONFIRMED_I = 1
DEATHS_I = 4
RECOVERED_I = 5


class Scraping:
    def __init__(self):
        self.URL = "https://es.wikipedia.org/wiki/Pandemia_de_enfermedad_por_coronavirus_de_2020_en_Argentina"
        self.html = requests.get(self.URL).text
        self.data_folder = "app/data"
        self.confirmed_file = os.path.join(self.data_folder, "time_series_confirmed.csv")
        self.deaths_file = os.path.join(self.data_folder, "time_series_deaths.csv")
        self.recovered_file = os.path.join(self.data_folder, "time_series_recovered.csv")
        self.process()

    def mergeCsv(self):
        # load csvs into memory
        confirmed_read = self.load_csv(self.confirmed_file)
        deaths_read = self.load_csv(self.deaths_file)
        recovered_read = self.load_csv(self.recovered_file)

        last_day_csv = confirmed_read[0][-1]
        today = datetime.strptime(datetime.now().strftime('%-m/%-d/%y'), '%m/%d/%y')
        replace_last = self.to_date(last_day_csv) == today

        with open(self.confirmed_file, "w") as c, \
            open(self.deaths_file, "w") as d, \
            open(self.recovered_file, "w") as r:

            writers = [csv.writer(c), csv.writer(d), csv.writer(r)]

            for i, row in enumerate(confirmed_read):
                if i == 0:
                    self.update_headers(row, writers, replace_last)
                else:
                    province = row[0]
                    confirmed_row = row
                    deaths_row = deaths_read[i]
                    recovered_row = recovered_read[i]
                    new_rows = [confirmed_row, deaths_row, recovered_row]

                    self.write_to_csvs(province, writers, new_rows, replace_last)

    def write_to_csvs(self, province, writers, rows, replace_last=False):
        [confirmed, deaths, recovered] = writers
        [confirmed_row, deaths_row, recovered_row] = rows
        indices = [CONFIRMED_I, DEATHS_I, RECOVERED_I]
        epidemiologia_by_province = self.to_dict(0, self.epidemiologia_table)

        for i, writer in enumerate(writers):
            row = rows[i]
            col_index = indices[i]
            new_val = epidemiologia_by_province[province][col_index]
            if replace_last:
                row[-1] = new_val
            else:
                row.append(new_val)
            writer.writerow(row)

    def update_headers(self, header, writers, replace_last=False):
        if not replace_last:
            header.append(datetime.now().strftime('%-m/%-d/%y'))
        for writer in writers:
            writer.writerow(header)

    def load_csv(self, file_path):
        rows = []
        file = open(file_path, "r")
        from_csv = csv.reader(file)
        rows.extend(from_csv)
        return rows

    def process(self):
        # 'Provincia', 'Casos confirmados', 'Población(proy. 2020)', 'Prevalencia(casos cadaMde hab)', 'Muertes confirmadas', 'Recuperaciones confirmadas'
        self.epidemiologia_table = parse_table(self.html, order=0)
        # 'Día', 'Casos confirmados', 'Casos acumulados', 'Nuevas muertes', 'Recuperaciones'
        # self.estadisticas_table = parse_table(self.html, order=1)
        self.mergeCsv()

    def to_date(self, date_time_str):
        return datetime.strptime(date_time_str, '%m/%d/%y')

    def parse_date(self, date):
        current_year = 20
        months = {
            "enero": 1,
            "febrero": 2,
            "marzo": 3,
            "abril": 4,
            "mayo": 5,
            "junio": 6,
            "julio": 7,
            "agosto": 8,
            "septiembre": 9,
            "octubre": 10,
            "noviembre": 11,
            "diciembre": 12
            }

        [day, month] = date.lower().split(" de ")
        formatted_date = f"{months[month]}/{day}/{current_year}"
        return formatted_date

    def to_dict(self, key_index, list):
        dictionary = {}
        for elem in list:
            dictionary[elem[key_index]] = elem
        return dictionary

if __name__ == "__main__":
    Scraping()
