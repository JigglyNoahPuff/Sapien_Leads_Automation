import scrapy
import apify



class YelpSpider(scrapy.Spider):
    name = 'yelp'

    def start_requests(self):
        urls = [r'https://www.yelp.com/biz/downtown-chiropractic-and-massage-therapy-salt-lake-city-5?osq=Chiropractor']
        
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)


    def parse(self, response):
        
        yield {
           "business_name" : response.css(".css-11q1g5y::text").get()
        }

