"""MongoDB 접속과 Vector Search 인덱스를 점검한다."""
import sys
from pathlib import Path

# scripts/ 디렉터리에서 직접 실행해도 프로젝트 루트를 모듈 경로에 포함한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pymongo.errors import PyMongoError

from app.config import settings
from app.rag.vector_store import _get_client


def main() -> None:
    if not settings.mongodb_uri:
        raise SystemExit("MONGODB_URI가 .env에 설정되지 않았습니다.")

    try:
        client = _get_client()
        client.admin.command("ping")
        collection = client[settings.mongodb_database][settings.mongodb_collection]
        print("MongoDB 연결: 성공")
        print(f"Database: {settings.mongodb_database}")
        print(f"Collection: {settings.mongodb_collection}")
        print(f"저장된 chunk: {collection.count_documents({})}개")

        indexes = list(collection.list_search_indexes())
        vector_index = next(
            (
                index
                for index in indexes
                if index.get("name") == settings.mongodb_vector_index
            ),
            None,
        )
        if vector_index is None:
            print(f"Vector Search 인덱스: '{settings.mongodb_vector_index}' 없음")
            print("Atlas에서 Vector Search 인덱스를 생성한 뒤 다시 실행하세요.")
            raise SystemExit(2)
        print(f"Vector Search 인덱스: {vector_index.get('status', '확인됨')}")
        if vector_index.get("status") != "READY":
            raise SystemExit("Vector Search 인덱스가 READY 상태가 아닙니다.")
    except PyMongoError as exc:
        raise SystemExit(
            f"MongoDB 점검 실패: {type(exc).__name__}: {exc}"
        ) from exc


if __name__ == "__main__":
    main()
