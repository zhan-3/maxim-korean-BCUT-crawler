from bs4 import BeautifulSoup
import requests
headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0"
}
content = requests.get("https://www.maximkorea.net/",headers).text 
soup = BeautifulSoup(content, "html.parser")
all_img= soup.find_all("p", attrs={"class":"price_color"})

for price in all_img:

    print(price.string[2:])