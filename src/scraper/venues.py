"""
会议配置与论文爬取
"""

from typing import List, Optional, Dict
from tqdm import tqdm

from .client import OpenReviewClient, create_client
from .models import Paper
from config import VENUES, VenueConfig


def parse_note_to_paper(note, venue: str, year: int) -> Optional[Paper]:
    """
    将 OpenReview Note 转换为 Paper 对象
    
    Args:
        note: OpenReview Note 对象
        venue: 会议名称
        year: 年份
        
    Returns:
        Paper 对象，如果解析失败返回 None
    """
    try:
        content = note.content
        
        # 获取标题
        title = content.get("title", {})
        if isinstance(title, dict):
            title = title.get("value", "")
        
        # 获取摘要
        abstract = content.get("abstract", {})
        if isinstance(abstract, dict):
            abstract = abstract.get("value", "")
        
        # 获取作者
        authors = content.get("authors", {})
        if isinstance(authors, dict):
            authors = authors.get("value", [])
        if isinstance(authors, str):
            authors = [authors]
        
        # 获取关键词
        keywords = content.get("keywords", {})
        if isinstance(keywords, dict):
            keywords = keywords.get("value", [])
        if isinstance(keywords, str):
            keywords = [keywords]
        
        # 构建 URL
        url = f"https://openreview.net/forum?id={note.id}"
        
        # PDF URL
        pdf_url = content.get("pdf", {})
        if isinstance(pdf_url, dict):
            pdf_url = pdf_url.get("value")
        if pdf_url and not pdf_url.startswith("http"):
            pdf_url = f"https://openreview.net{pdf_url}"
        
        return Paper(
            id=note.id,
            title=title,
            abstract=abstract,
            authors=authors if isinstance(authors, list) else [],
            venue=venue,
            year=year,
            url=url,
            keywords=keywords if isinstance(keywords, list) else [],
            pdf_url=pdf_url,
        )
    except Exception as e:
        print(f"解析论文失败: {e}")
        return None


def scrape_venue(
    venue_config: VenueConfig,
    year: int,
    client: Optional[OpenReviewClient] = None,
    limit: Optional[int] = None,
    show_progress: bool = True,
) -> List[Paper]:
    """
    爬取指定会议指定年份的论文
    
    Args:
        venue_config: 会议配置
        year: 年份
        client: OpenReview 客户端（可选，默认创建新的）
        limit: 限制返回论文数量
        show_progress: 是否显示进度条
        
    Returns:
        论文列表
    """
    if client is None:
        client = create_client()
    
    venue_id = venue_config.venue_id_pattern.format(year=year)
    papers = []
    
    print(f"\n🔍 正在爬取 {venue_config.name} {year}...")
    
    notes = list(client.get_accepted_papers(venue_id, limit=limit))
    
    if show_progress:
        notes = tqdm(notes, desc=f"{venue_config.name} {year}")
    
    for note in notes:
        paper = parse_note_to_paper(note, venue_config.name, year)
        if paper:
            papers.append(paper)
    
    print(f"✅ {venue_config.name} {year}: 获取 {len(papers)} 篇论文")
    return papers


def scrape_all_venues(
    venues: Optional[Dict[str, VenueConfig]] = None,
    years: Optional[List[int]] = None,
    limit_per_venue: Optional[int] = None,
    show_progress: bool = True,
) -> List[Paper]:
    """
    爬取所有配置的会议论文
    
    Args:
        venues: 会议配置字典（默认使用 config 中的配置）
        years: 要爬取的年份列表（默认使用各会议配置的年份）
        limit_per_venue: 每个会议年份的论文数量限制
        show_progress: 是否显示进度条
        
    Returns:
        所有论文列表
    """
    if venues is None:
        venues = VENUES
    
    client = create_client()
    all_papers = []
    
    for venue_name, venue_config in venues.items():
        venue_years = years if years is not None else venue_config.years
        
        for year in venue_years:
            try:
                papers = scrape_venue(
                    venue_config,
                    year,
                    client=client,
                    limit=limit_per_venue,
                    show_progress=show_progress,
                )
                all_papers.extend(papers)
            except Exception as e:
                print(f"❌ 爬取 {venue_name} {year} 失败: {e}")
                continue
    
    print(f"\n📊 总计爬取 {len(all_papers)} 篇论文")
    return all_papers
