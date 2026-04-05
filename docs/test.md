 # 跑全部測試
  python3 -m pytest tests/ -v

  # 跑單一模組
  python3 -m pytest tests/services/test_user_service.py -v

  # 跑單一 class
  python3 -m pytest tests/services/test_trip_service.py::TestCreateTrip -v

  # 跑單一 test
  python3 -m pytest tests/ai/test_cag_builder.py::TestBuildUserContext::test_returns_from_redis_cache -v

  # 看覆蓋率（需要 pip3 install pytest-cov）
  python3 -m pytest tests/ --cov=app --cov-report=term-missing