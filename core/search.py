def search_internet(query: str, max_results: int = 5) -> list[dict]:

    try:
        from ddgs import DDGS

        limit = max(1, min(int(max_results), 10))
        raw_results = DDGS().text(query, max_results=limit)

        results = []
        for item in raw_results or []:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("href", item.get("url", "")),
                "body": item.get("body", "")
            })

        return results

    except Exception:
        return []


def format_results(results: list[dict]) -> str:
    if not results:
        return "Информация из интернета не найдена."

    formatted = []
    for index, item in enumerate(results, start=1):
        formatted.append(
            f"Источник [{index}]\n"
            f"Название: {item.get('title', '')}\n"
            f"URL: {item.get('url', '')}\n"
            f"Описание: {item.get('body', '')}"
        )

    return "\n\n".join(formatted)
