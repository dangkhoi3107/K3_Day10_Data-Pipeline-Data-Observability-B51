"""Interactive Demo CLI for Data Pipeline & Data Observability RAG System."""
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_dir))

from core.config import load_settings
from core.utils import read_json
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    settings = load_settings()
    print("================================================================")
    print("  🚀 DATA PIPELINE & DATA OBSERVABILITY RAG DEMO CLI")
    print("================================================================\n")
    print("Lựa chọn chế độ demo:")
    print(" [1] 🏃 Run Baseline Pipeline (Pha 1: Data Ingestion -> Clean -> Index -> Observability)")
    print(" [2] 💥 Run Corruption & Repair Flow (Pha 2: Corruption -> Evaluate -> Repair -> Compare)")
    print(" [3] 🔍 Live RAG QA Search (Đặt câu hỏi truy vấn bài báo khoa học live)")
    print(" [4] 📊 Xem báo cáo so sánh Baseline vs Corrupted vs Repaired")
    print(" [0] Thoát\n")

    choice = input("Nhập lựa chọn của bạn (0-4): ").strip()

    if choice == "1":
        print("\n▶️ Đang chạy Baseline Pipeline...\n")
        from pipelines.phase1 import main as phase1_main
        phase1_main()
    elif choice == "2":
        print("\n▶️ Đang chạy Corruption & Repair Flow...\n")
        from pipelines.corruption_flow import main as corruption_main
        corruption_main()
    elif choice == "3":
        print("\n🔍 Khởi tạo Vector Search Engine...")
        if not settings.paths.embeddings_json.exists():
            print("❌ Chưa tìm thấy Vector Index! Vui lòng chạy lựa chọn [1] trước.")
            return
        index = LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json)
        print(f"✅ Đã tải index ChromaDB với {len(index.documents)} bài báo sạch.\n")

        print("--- Gợi ý các câu hỏi mẫu trong frozen eval set ---")
        test_set = read_json(settings.paths.eval_testset) if settings.paths.eval_testset.exists() else []
        for i, q in enumerate(test_set[:3], 1):
            print(f"  {i}. {q['question']}")
        print("---------------------------------------------------\n")

        while True:
            q_text = input("👉 Nhập câu hỏi (hoặc gõ 'exit' để thoát): ").strip()
            if not q_text or q_text.lower() in ("exit", "quit", "q"):
                break
            result = answer_question(q_text, settings=settings, index=index)
            print("\n---------------------------------------------------")
            print(f"❓ Câu hỏi: {result.question}")
            print(f"💡 Trả lời: {result.answer}")
            print(f"📚 Documents tìm thấy: {result.retrieved_doc_ids}")
            print("Titles top:")
            for title in result.retrieved_titles[:2]:
                print(f"  • {title}")
            print("---------------------------------------------------\n")
    elif choice == "4":
        report_file = settings.paths.comparison_report
        if report_file.exists():
            print("\n---------------------------------------------------")
            print(report_file.read_text(encoding="utf-8"))
            print("---------------------------------------------------\n")
        else:
            print("❌ Chưa có báo cáo! Vui lòng chạy lựa chọn [2] trước.")
    else:
        print("Cảm ơn bạn đã dùng Demo CLI!")

if __name__ == "__main__":
    main()
