from pipeline.config import PROJECT_NAME, BASE_DIR

def main():
    print("=" * 40)
    print(PROJECT_NAME)
    print("=" * 40)
    print(f"Project location: {BASE_DIR}")
    print("Project configuration loaded successfully!")

if __name__ == "__main__":
    main()