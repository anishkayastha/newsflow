import json, os, re, hashlib, feedparser, boto3
from datetime import datetime, timezone

PIPELINE_BUCKET = os.environ.get('PIPELINE_BUCKET', '')
s3  = boto3.client('s3')
cw  = boto3.client('cloudwatch')

MAX_ARTICLES_PER_FEED = 25

RSS_FEEDS = [
    # Business
    ('The Economist','Business','https://www.economist.com/latest/rss.xml'),
    ('Financial Times','Business','https://www.ft.com/?format=rss'),
    ('Bloomberg','Business','https://feeds.bloomberg.com/markets/news.rss'),
    ('WSJ Business','Business','https://feeds.a.dj.com/rss/RSSMarketsMain.xml'),
    ('MarketWatch','Business','https://www.marketwatch.com/rss/topstories'),
    ('Forbes','Business','https://www.forbes.com/business/feed/'),
    ('Business Insider','Business','https://www.businessinsider.com/rss'),
    ('CNBC Top','Business','https://www.cnbc.com/id/100003114/device/rss/rss.html'),
    ('CNBC Markets','Business','https://www.cnbc.com/id/20910258/device/rss/rss.html'),
    ('BBC Business','Business','https://feeds.bbci.co.uk/news/business/rss.xml'),
    ('Inc. Magazine','Business','https://www.inc.com/rss'),
    ('Yahoo Finance','Business','https://finance.yahoo.com/rss/topstories'),
    ('CFO Dive','Business','https://www.cfodive.com/feeds/news/'),
    ('Supply Chain Dive','Business','https://www.supplychaindive.com/feeds/news/'),
    ('Crunchbase','Business','https://news.crunchbase.com/feed/'),
    ('Seeking Alpha','Business','https://seekingalpha.com/feed.xml'),
    ('SiliconANGLE Biz','Business','https://siliconangle.com/feed/'),
    ('Fortune','Business','https://fortune.com/feed/'),
    ('MIT Sloan Review','Business','https://sloanreview.mit.edu/feed/'),
    ('TechCrunch Startup','Business','https://techcrunch.com/category/startups/feed/'),
    ('HR Dive','Business','https://www.hrdive.com/feeds/news/'),
    ('Axios Business','Business','https://www.axios.com/feeds/feed.rss'),
    ('Economic Times','Business','https://economictimes.indiatimes.com/rssfeedstopstories.cms'),
    ('Reuters Business GN','Business','https://news.google.com/rss/search?q=reuters+business&hl=en&gl=US&ceid=US:en'),
    # Entertainment
    ('Variety','Entertainment','https://variety.com/feed/'),
    ('Hollywood Reporter','Entertainment','https://www.hollywoodreporter.com/feed/'),
    ('Deadline','Entertainment','https://deadline.com/feed/'),
    ('IndieWire','Entertainment','https://www.indiewire.com/feed/'),
    ('Rolling Stone','Entertainment','https://www.rollingstone.com/music/music-news/feed/'),
    ('Billboard','Entertainment','https://www.billboard.com/feed/'),
    ('E! Online','Entertainment','https://www.eonline.com/syndication/feeds/rssfeeds/topstories.xml'),
    ('TMZ','Entertainment','https://www.tmz.com/rss.xml'),
    ('Pitchfork','Entertainment','https://pitchfork.com/feed/feed-news/rss'),
    ('Screen Rant','Entertainment','https://screenrant.com/feed/'),
    ('IGN','Entertainment','https://feeds.feedburner.com/ign/news'),
    ('Polygon','Entertainment','https://www.polygon.com/rss/index.xml'),
    ('GameSpot','Entertainment','https://www.gamespot.com/feeds/mashup/'),
    ('Kotaku','Entertainment','https://kotaku.com/rss'),
    ('AV Club','Entertainment','https://www.avclub.com/rss'),
    ('Collider','Entertainment','https://collider.com/feed/'),
    # Environment
    ('BBC Environment','Environment','https://feeds.bbci.co.uk/news/science_and_environment/rss.xml'),
    ('InsideClimate News','Environment','https://insideclimatenews.org/feed/'),
    ('Carbon Brief','Environment','https://www.carbonbrief.org/feed'),
    ('ScienceDaily Env','Environment','https://www.sciencedaily.com/rss/earth_climate.xml'),
    ('Mongabay','Environment','https://news.mongabay.com/feed/'),
    ('CleanTechnica','Environment','https://cleantechnica.com/feed/'),
    ('Electrek','Environment','https://electrek.co/feed/'),
    ('NPR Environment','Environment','https://feeds.npr.org/1025/rss.xml'),
    ('Grist','Environment','https://grist.org/feed/'),
    ('DeSmog','Environment','https://www.desmog.com/feed/'),
    ('Anthropocene Mag','Environment','https://www.anthropocenemagazine.org/feed/'),
    ('Greenpeace','Environment','https://www.greenpeace.org/international/feed/'),
    ('EcoWatch','Environment','https://www.ecowatch.com/feed'),
    ('Reuters Climate GN','Environment','https://news.google.com/rss/search?q=climate+environment&hl=en&gl=US&ceid=US:en'),
    ('NASA Earth Obs','Environment','https://earthobservatory.nasa.gov/feeds/earth-observatory.rss'),
    ('Climate Home News','Environment','https://www.climatechangenews.com/feed/'),
    ('Yale Climate Conn.','Environment','https://yaleclimateconnections.org/feed/'),
    ('World Wildlife Fund','Environment','https://www.worldwildlife.org/stories.rss'),
    ('Columbia Climate','Environment','https://news.climate.columbia.edu/feed/'),
    ('PV Magazine','Environment','https://www.pv-magazine.com/feed/'),
    ('Guardian Climate','Environment','https://www.theguardian.com/environment/climate-crisis/rss'),
    # Health
    ('BBC Health','Health','https://feeds.bbci.co.uk/news/health/rss.xml'),
    ('NHS England','Health','https://www.england.nhs.uk/feed/'),
    ('WHO News','Health','https://www.who.int/rss-feeds/news-english.xml'),
    ('Healthline','Health','https://www.healthline.com/rss/health-news'),
    ('STAT News','Health','https://www.statnews.com/feed/'),
    ('The Lancet','Health','https://www.thelancet.com/rssfeedstopstories.xml'),
    ('NEJM','Health','https://www.nejm.org/action/showFeed?jc=nejm&type=etoc&feed=rss'),
    ('NPR Health','Health','https://feeds.npr.org/1128/rss.xml'),
    ('Guardian Health','Health','https://www.theguardian.com/society/health/rss'),
    ('ScienceDaily Health','Health','https://www.sciencedaily.com/rss/health_medicine.xml'),
    ('Health Affairs','Health','https://www.healthaffairs.org/action/showFeed?type=etoc&feed=rss&jc=hlthaff'),
    ('Fierce Healthcare','Health','https://www.fiercehealthcare.com/rss/xml'),
    ('ABC Health','Health','https://abcnews.go.com/abcnews/healthheadlines'),
    ('CBS News Health','Health','https://www.cbsnews.com/latest/rss/health'),
    ('Medical Xpress','Health','https://medicalxpress.com/rss-feed/'),
    ('MedPage Today','Health','https://www.medpagetoday.com/rss/headlines.xml'),
    ('JAMA Network','Health','https://jamanetwork.com/rss/site_3/67.xml'),
    ('Reuters Health GN','Health','https://news.google.com/rss/search?q=health+medicine+research&hl=en&gl=US&ceid=US:en'),
    ('Infectious Disease','Health','https://www.healio.com/rss/infectious-disease'),
    ('CDC Health GN','Health','https://news.google.com/rss/search?q=CDC+health&hl=en&gl=US&ceid=US:en'),
    ('Fierce Pharma','Health','https://www.fiercepharma.com/rss/xml'),
    ('SELF Magazine','Health','https://www.self.com/feed/'),
    ('Healio Primary Care','Health','https://www.healio.com/rss/primary-care'),
    ('AMA News','Health','https://www.ama-assn.org/rss.xml'),
    # Science
    ('ScienceDaily','Science','https://www.sciencedaily.com/rss/top.xml'),
    ('NASA Breaking','Science','https://www.nasa.gov/rss/dyn/breaking_news.rss'),
    ('NASA JPL','Science','https://www.jpl.nasa.gov/feeds/news'),
    ('New Scientist','Science','https://www.newscientist.com/feed/home/'),
    ('Nature','Science','https://www.nature.com/nature.rss'),
    ('Science Magazine','Science','https://www.science.org/rss/news_current.xml'),
    ('Phys.org','Science','https://phys.org/rss-feed/'),
    ('Space.com','Science','https://www.space.com/feeds/all'),
    ('EarthSky','Science','https://earthsky.org/feed/'),
    ('Live Science','Science','https://www.livescience.com/feeds/all'),
    ('Quanta Magazine','Science','https://api.quantamagazine.org/feed/'),
    ('Ars Technica Sci','Science','https://feeds.arstechnica.com/arstechnica/science'),
    ('Guardian Science','Science','https://www.theguardian.com/science/rss'),
    ('BBC Science','Science','https://feeds.bbci.co.uk/news/science_and_environment/rss.xml'),
    ('Popular Science','Science','https://www.popsci.com/feed/'),
    ('MIT Research','Science','https://news.mit.edu/rss/research'),
    ('ScienceAlert','Science','https://www.sciencealert.com/feed'),
    ('Wired Science','Science','https://www.wired.com/feed/category/science/latest/rss'),
    ('Science News','Science','https://www.sciencenews.org/feed'),
    ('Sky & Telescope','Science','https://skyandtelescope.org/feed/'),
    ('AAAS News','Science','https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science'),
    ('Smithsonian Science','Science','https://www.smithsonianmag.com/rss/science-nature/'),
    ('Physics World','Science','https://physicsworld.com/feed/'),
    ('PNAS','Science','https://www.pnas.org/rss/current.xml'),
    ('New Atlas','Science','https://newatlas.com/index.rss'),
    # Sports
    ('ESPN','Sports','https://www.espn.com/espn/rss/news'),
    ('BBC Sport','Sports','https://feeds.bbci.co.uk/sport/rss.xml'),
    ('CBS Sports','Sports','https://www.cbssports.com/rss/headlines/'),
    ('Sky Sports','Sports','https://www.skysports.com/rss/12040'),
    ('Yahoo Sports','Sports','https://sports.yahoo.com/rss/'),
    ('Fox Sports','Sports','https://api.foxsports.com/v2/content/optimized-rss?partnerKey=MB0Wehpmuj2lUhuRhQaafhBjAJqaPU244mlTDK1i&size=30'),
    ('LA Times Sports','Sports','https://www.latimes.com/sports/rss2.0.xml'),
    ('Washington Times','Sports','https://www.washingtontimes.com/rss/headlines/sports/'),
    ('Deadspin','Sports','https://deadspin.com/rss'),
    ('Pro Football Talk','Sports','https://profootballtalk.nbcsports.com/feed/'),
    ('MLB.com','Sports','https://www.mlb.com/feeds/news/rss.xml'),
    ('Cycling News','Sports','https://www.cyclingnews.com/rss.xml'),
    ('Formula 1','Sports','https://www.formula1.com/content/fom-website/en/latest/all.xml'),
    ('SMH Sport','Sports','https://www.smh.com.au/rss/sport.xml'),
    ('Boston.com Sports','Sports','https://www.boston.com/category/sports/feed/'),
    ('Boxing News','Sports','https://boxingnewsonline.net/feed/'),
    ('Essentially Sports','Sports','https://www.essentiallysports.com/feed/'),
    ('Guardian Sport','Sports','https://www.theguardian.com/sport/rss'),
    ('FourFourTwo','Sports','https://www.fourfourtwo.com/rss.xml'),
    ('Sportstar','Sports','https://sportstar.thehindu.com/feeder/default.rss'),
    ('GiveMeSport','Sports','https://www.givemesport.com/feed/'),
    ('90min.com','Sports','https://www.90min.com/feed'),
    ('NBC Sports','Sports','https://www.nbcsports.com/feed/rss'),
    ('BBC Football','Sports','https://feeds.bbci.co.uk/sport/football/rss.xml'),
    # Technology
    ('TechCrunch','Technology','https://techcrunch.com/feed/'),
    ('The Verge','Technology','https://www.theverge.com/rss/index.xml'),
    ('Ars Technica','Technology','https://feeds.arstechnica.com/arstechnica/index'),
    ('Wired','Technology','https://www.wired.com/feed/rss'),
    ('VentureBeat','Technology','https://venturebeat.com/feed/'),
    ('Hacker News','Technology','https://news.ycombinator.com/rss'),
    ('The Register','Technology','https://www.theregister.com/headlines.atom'),
    ('MIT Tech Review','Technology','https://www.technologyreview.com/feed/'),
    ('ZDNet','Technology','https://www.zdnet.com/news/rss.xml'),
    ('Engadget','Technology','https://www.engadget.com/rss.xml'),
    ('TechRadar','Technology','https://www.techradar.com/rss'),
    ('Gizmodo','Technology','https://gizmodo.com/feed/rss'),
    ('CNET','Technology','https://www.cnet.com/rss/news/'),
    ('9to5Mac','Technology','https://9to5mac.com/feed/'),
    ('9to5Google','Technology','https://9to5google.com/feed/'),
    ('Android Authority','Technology','https://www.androidauthority.com/feed/'),
    ('MacRumors','Technology','https://feeds.macrumors.com/MacRumors-All'),
    ("Tom's Hardware",'Technology','https://www.tomshardware.com/feeds/all'),
    ('Product Hunt','Technology','https://www.producthunt.com/feed'),
    ('TechRepublic','Technology','https://www.techrepublic.com/rssfeeds/articles/'),
    ('Slashdot','Technology','https://rss.slashdot.org/Slashdot/slashdotMain'),
    ('ReadWrite','Technology','https://readwrite.com/feed/'),
    ('SiliconANGLE','Technology','https://siliconangle.com/feed/'),
    ('Techmeme','Technology','https://www.techmeme.com/feed.xml'),
    ('MIT News AI','Technology','https://news.mit.edu/rss/topic/artificial-intelligence2'),
    ('Google AI Blog','Technology','https://blog.research.google/feeds/posts/default'),
    ('DeepMind','Technology','https://deepmind.google/blog/rss.xml'),
    ('IEEE Spectrum','Technology','https://feeds.feedburner.com/IeeeSpectrumFullText'),
    ('Digital Trends','Technology','https://www.digitaltrends.com/feed/'),
    ('TechSpot','Technology','https://www.techspot.com/backend.xml'),
    # World Politics
    ('BBC World','World Politics','https://feeds.bbci.co.uk/news/world/rss.xml'),
    ('Al Jazeera','World Politics','https://www.aljazeera.com/xml/rss/all.xml'),
    ('The Guardian World','World Politics','https://www.theguardian.com/world/rss'),
    ('NPR World','World Politics','https://feeds.npr.org/1004/rss.xml'),
    ('ABC News Intl','World Politics','https://abcnews.go.com/abcnews/internationalheadlines'),
    ('CBS News World','World Politics','https://www.cbsnews.com/latest/rss/world'),
    ('NBC News World','World Politics','https://feeds.nbcnews.com/nbcnews/public/world'),
    ('PBS World','World Politics','https://www.pbs.org/newshour/feeds/rss/world'),
    ('VOX World','World Politics','https://www.vox.com/rss/world-politics/index.xml'),
    ('The Hill','World Politics','https://thehill.com/homenews/feed/'),
    ('Foreign Policy','World Politics','https://foreignpolicy.com/feed/'),
    ('Foreign Affairs','World Politics','https://www.foreignaffairs.com/rss.xml'),
    ('Deutsche Welle','World Politics','https://rss.dw.com/rdf/rss-en-all'),
    ('France 24','World Politics','https://www.france24.com/en/rss'),
    ('Sky News World','World Politics','https://feeds.skynews.com/feeds/rss/world.xml'),
    ('Channel NewsAsia','World Politics','https://www.channelnewsasia.com/rssfeeds/8395986'),
    ('SCMP','World Politics','https://www.scmp.com/rss/91/feed'),
    ('The Hindu Intl','World Politics','https://www.thehindu.com/news/international/feeder/default.rss'),
    ('Times of India','World Politics','https://timesofindia.indiatimes.com/rssfeeds/296589292.cms'),
    ('Hong Kong FP','World Politics','https://hongkongfp.com/feed/'),
    ('Middle East Eye','World Politics','https://www.middleeasteye.net/rss'),
    ('The Conversation','World Politics','https://theconversation.com/us/politics/articles.atom'),
    ('Global Voices','World Politics','https://globalvoices.org/feed/'),
    ('The Atlantic','World Politics','https://feeds.feedburner.com/TheAtlantic'),
    ('Euronews','World Politics','https://www.euronews.com/rss?format=mrss&level=theme&name=news'),
    ('AP News World GN','World Politics','https://news.google.com/rss/search?q=AP+news+world&hl=en&gl=US&ceid=US:en'),
]

AUTHORITY = {
    'BBC':0.98,'BBC World':0.98,'BBC Sport':0.98,'BBC Health':0.98,'BBC Business':0.98,
    'BBC Science':0.98,'BBC Environment':0.98,'BBC Football':0.98,
    'The Guardian World':0.95,'Guardian Science':0.95,'Guardian Health':0.95,
    'Guardian Sport':0.95,'Guardian Climate':0.95,
    'Al Jazeera':0.92,'NPR World':0.92,'NPR Health':0.92,'NPR Environment':0.92,
    'Bloomberg':0.91,'The Economist':0.91,'Financial Times':0.91,'WSJ Business':0.90,
    'Nature':0.95,'NEJM':0.95,'The Lancet':0.95,'Science Magazine':0.95,
    'JAMA Network':0.94,'PNAS':0.93,
    'NASA Breaking':0.92,'NASA JPL':0.92,'NASA Earth Obs':0.92,'WHO News':0.92,
    'TechCrunch':0.88,'Ars Technica':0.88,'Ars Technica Sci':0.88,
    'MIT Tech Review':0.90,'MIT News AI':0.90,'MIT Research':0.90,
    'Wired':0.86,'ESPN':0.85,'CBS Sports':0.85,
    'Deutsche Welle':0.88,'France 24':0.87,'Foreign Policy':0.90,'Foreign Affairs':0.90,
}

def clean_html(text):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text)).strip()

def lambda_handler(event, context):
    articles = []
    feed_ok = 0

    for source_name, topic, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url, request_headers={'User-Agent': 'NewsFlow/1.0'})
            count = 0
            for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
                title   = getattr(entry, 'title', '').strip()
                summary = clean_html(getattr(entry, 'summary', '') or
                                     getattr(entry, 'description', '') or '')
                if len(title) < 10:
                    continue
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                    except Exception:
                        pass
                if not published:
                    published = datetime.now(timezone.utc).isoformat()
                article_id = hashlib.md5(f'{url}{title}'.encode()).hexdigest()
                articles.append({
                    'id': article_id,
                    'title': title,
                    'summary': summary[:500],
                    'text': title + '. ' + summary[:500],
                    'source': source_name,
                    'topic': topic,
                    'published': published,
                    'ingested_at': datetime.now(timezone.utc).isoformat(),
                    'authority': AUTHORITY.get(source_name, 0.50),
                    'article_url': getattr(entry, 'link', '') or '',
                })
                count += 1
            if count > 0:
                feed_ok += 1
        except Exception as e:
            print(f'[WARN] {source_name}: {e}')

    if not articles:
        print('[ERROR] Empty batch — no articles ingested')
        cw.put_metric_data(Namespace='NewsFlow', MetricData=[
            {'MetricName': 'ArticlesIngested', 'Value': 0, 'Unit': 'Count'},
        ])
        return {'status': 'error', 'reason': 'empty_batch'}

    # Write ALL articles as a single S3 object so consumer sees the full dataset.
    # This guarantees one Lambda invocation → one DBSCAN run → no duplicate clusters.
    timestamp  = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    s3_key     = f'pipeline/articles-{timestamp}.json'
    body_bytes = json.dumps({'articles': articles, 'ingested_at': timestamp}).encode('utf-8')

    s3.put_object(
        Bucket      = PIPELINE_BUCKET,
        Key         = s3_key,
        Body        = body_bytes,
        ContentType = 'application/json',
    )
    print(f'[OK] {len(articles)} articles from {feed_ok}/{len(RSS_FEEDS)} feeds → s3://{PIPELINE_BUCKET}/{s3_key}')

    cw.put_metric_data(Namespace='NewsFlow', MetricData=[
        {'MetricName': 'ArticlesIngested', 'Value': len(articles), 'Unit': 'Count'},
        {'MetricName': 'FeedsActive',      'Value': feed_ok,       'Unit': 'Count'},
    ])
    return {'status': 'ok', 'articles': len(articles), 'feeds_ok': feed_ok, 's3_key': s3_key}