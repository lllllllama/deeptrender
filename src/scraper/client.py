"""
OpenReview API 客户端封装
"""

import time
from typing import List, Optional, Iterator
import openreview
from openreview.api import OpenReviewClient as ORClient

from config import OPENREVIEW_API_URL, OPENREVIEW_USERNAME, OPENREVIEW_PASSWORD


class OpenReviewClient:
    """OpenReview API 客户端"""
    
    def __init__(
        self,
        baseurl: str = OPENREVIEW_API_URL,
        username: str = OPENREVIEW_USERNAME,
        password: str = OPENREVIEW_PASSWORD,
    ):
        """
        初始化客户端
        
        Args:
            baseurl: API 基础 URL
            username: OpenReview 用户名（可选）
            password: OpenReview 密码（可选）
        """
        self.baseurl = baseurl
        
        # 创建客户端（无需登录也可以访问公开数据）
        if username and password:
            self.client = ORClient(
                baseurl=baseurl,
                username=username,
                password=password,
            )
        else:
            self.client = ORClient(baseurl=baseurl)
    
    def get_submissions(
        self,
        venue_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Iterator[openreview.api.Note]:
        """
        获取会议的所有提交论文
        
        Args:
            venue_id: 会议 ID，如 "ICLR.cc/2024/Conference"
            limit: 限制返回数量（None 表示全部）
            offset: 起始偏移量
            
        Yields:
            论文 Note 对象
        """
        # 获取接受的论文
        invitation = f"{venue_id}/-/Submission"
        
        try:
            # 尝试获取 Blind Submission（某些会议使用）
            notes = list(self.client.get_all_notes(
                invitation=invitation,
                details="original",
            ))
            
            if not notes:
                # 尝试其他常见的 invitation 格式
                alternative_invitations = [
                    f"{venue_id}/-/Blind_Submission",
                    f"{venue_id}/-/blind-submission",
                ]
                for alt_invitation in alternative_invitations:
                    try:
                        notes = list(self.client.get_all_notes(
                            invitation=alt_invitation,
                            details="original",
                        ))
                        if notes:
                            break
                    except Exception:
                        continue
        except Exception as e:
            print(f"获取论文失败 ({venue_id}): {e}")
            return
        
        # 应用 offset 和 limit
        if offset > 0:
            notes = notes[offset:]
        if limit is not None:
            notes = notes[:limit]
        
        for note in notes:
            yield note
    
    def get_accepted_papers(
        self,
        venue_id: str,
        limit: Optional[int] = None,
    ) -> Iterator[openreview.api.Note]:
        """
        获取会议接受的论文（通过检查 decision）
        
        Args:
            venue_id: 会议 ID
            limit: 限制返回数量
            
        Yields:
            接受的论文 Note 对象
        """
        count = 0
        for note in self.get_submissions(venue_id, limit=None):
            # 检查是否接受（某些会议可能没有明确的 decision 字段）
            # 这里简单返回所有提交，因为大多数顶会只显示接受的论文
            yield note
            count += 1
            if limit is not None and count >= limit:
                break
            # 添加小延迟避免请求过于频繁
            time.sleep(0.01)


def create_client() -> OpenReviewClient:
    """创建默认客户端"""
    return OpenReviewClient()
