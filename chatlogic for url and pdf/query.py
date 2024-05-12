import os
from bs4 import BeautifulSoup
import trafilatura 
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.chains.question_answering import load_qa_chain
from langchain_community.llms import OpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain_community.document_loaders import PyPDFium2Loader
from langchain.docstore.document import Document
import requests
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from urllib.parse import urljoin

class PDFQuery:
    def __init__(self, openai_api_key=None):
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        os.environ["OPENAI_API_KEY"] = openai_api_key
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.llm = ChatOpenAI(temperature=0, model="gpt-4", openai_api_key=openai_api_key)
        self.chain = None
        self.db = None
        self.ingested_documents = []

    def ask(self, question: str) -> str:
        if self.chain is None:
            return "Please, add a document."
        docs = self.db.get_relevant_documents(question)
        return self.chain.run(input_documents=docs, question=question)

    def ingest(self, file_path: os.PathLike) -> None:
        loader = PyPDFium2Loader(file_path)
        documents = loader.load()
        splitted_documents = self.text_splitter.split_documents(documents)
        self.db = Chroma.from_documents(splitted_documents, self.embeddings).as_retriever()
        self.chain = load_qa_chain(ChatOpenAI(temperature=0), chain_type="stuff")
        self.ingested_documents.extend(documents)

    def forget(self):
        self.db = None
        self.chain = None

class WebQuery:
    def __init__(self, openai_api_key=None):
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        os.environ["OPENAI_API_KEY"] = openai_api_key
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.llm = OpenAI(temperature=0, model="gpt-4", openai_api_key=openai_api_key)
        self.chain = None
        self.db = None
        self.ingested_documents = []
        self.processed_links = set()  # Keep track of processed links


    def ask(self, question: str) -> str:
        if self.chain is None:
            return "Please, add a document."

        docs = self.db.get_relevant_documents(question)
        answer = self.chain.run(input_documents=docs, question=question)

        # Include links in the answer
        if docs:
            source_links = [doc.metadata.get("source", "") for doc in docs]
            source_links_str = "\n".join([f"For more information, follow link: {link}" for link in source_links])
        answer += f"\n\nLinks:\n{source_links_str}"

        return answer + f"\n\nLinks:\n{source_links_str}"

    def ingest(self, url: str) -> str:
        # Skip if the link has already been processed
        if url in self.processed_links:
            print(f"Link {url} has already been processed. Skipping.")
            return "Skipped"

        # Generate sitemap for the given URL
        sitemap_xml = Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
        self.crawl_and_append_to_sitemap(url, sitemap_xml, depth=2)

        # Extract links from the sitemap and fetch content
        links = [loc.text for loc in sitemap_xml.findall('.//loc')]
        documents = []

        for link in links:
            # Skip if the link has already been processed
            if link in self.processed_links:
                print(f"Link {link} has already been processed. Skipping.")
                continue

            result = trafilatura.extract(trafilatura.fetch_url(link))
            if result:
                documents.append(Document(page_content=result, metadata={"source": link}))
                self.processed_links.add(link)  # Mark link as processed
            else:
                print(f"Failed to extract content from {link}. Skipping.")

        splitted_documents = self.text_splitter.split_documents(documents)
        self.db = Chroma.from_documents(splitted_documents, self.embeddings).as_retriever()
        self.chain = load_qa_chain(OpenAI(temperature=0), chain_type="stuff")
        self.ingested_documents.extend(documents)
        return "Success"

    def crawl_and_append_to_sitemap(self, base_url, sitemap_xml, depth=2):
        if depth <= 0:
            return sitemap_xml

        urls_on_page, _ = self.get_urls_from_page(base_url)

        for url in urls_on_page:
            full_url = urljoin(base_url, url)
            url_element = SubElement(sitemap_xml, 'url')
            loc_element = SubElement(url_element, 'loc')
            loc_element.text = full_url

            # Recursively crawl and append links from the current URL
            self.crawl_and_append_to_sitemap(full_url, sitemap_xml, depth - 1)

    def get_urls_from_page(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extracting regular links
            urls = [a['href'] for a in soup.find_all('a', href=True) if not a['href'].startswith('mailto:')]

            return urls, []
        else:
            print(f"Failed to retrieve content from {url}. Status code: {response.status_code}")
            return [], []

    def forget(self):
        self.db = None
        self.chain = None



