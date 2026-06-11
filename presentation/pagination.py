from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


class PaginationError(ValueError):
    pass


DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def get_request_value(request, key):
    return _get_request_value(request, key)


def _get_request_value(request, key):
    if hasattr(request, 'data') and request.data is not None:
        value = request.data.get(key)
        if value is not None and value != '':
            return value
    if hasattr(request, 'query_params'):
        return request.query_params.get(key)
    return request.GET.get(key)


def get_pagination_params(
    request,
    *,
    default_page=DEFAULT_PAGE,
    default_page_size=DEFAULT_PAGE_SIZE,
    max_page_size=MAX_PAGE_SIZE,
):
    page_raw = _get_request_value(request, 'page')
    page_size_raw = (
        _get_request_value(request, 'page_size')
        or _get_request_value(request, 'per_page')
    )

    try:
        page = int(page_raw) if page_raw not in (None, '') else default_page
        page_size = (
            int(page_size_raw)
            if page_size_raw not in (None, '')
            else default_page_size
        )
    except (TypeError, ValueError) as exc:
        raise PaginationError('page и page_size должны быть целыми числами') from exc

    if page < 1:
        raise PaginationError('page должен быть >= 1')
    if page_size < 1:
        raise PaginationError('page_size должен быть >= 1')
    if page_size > max_page_size:
        raise PaginationError(f'page_size не может превышать {max_page_size}')

    return page, page_size


def paginate_queryset(
    queryset,
    request,
    *,
    results_key='data',
    item_serializer=None,
    default_page_size=DEFAULT_PAGE_SIZE,
    max_page_size=MAX_PAGE_SIZE,
):
    page_number, page_size = get_pagination_params(
        request,
        default_page_size=default_page_size,
        max_page_size=max_page_size,
    )

    paginator = Paginator(queryset, page_size)
    total_count = paginator.count
    total_pages = paginator.num_pages if total_count else 0

    try:
        page_obj = paginator.page(page_number)
        current_page = page_obj.number
        items = page_obj.object_list
    except PageNotAnInteger:
        current_page = DEFAULT_PAGE
        items = paginator.page(DEFAULT_PAGE).object_list if total_count else []
    except EmptyPage:
        current_page = page_number
        items = []

    if item_serializer is not None:
        items = [item_serializer(item) for item in items]

    return {
        'count': total_count,
        'page_size': page_size,
        'total_pages': total_pages,
        'page': current_page,
        results_key: items,
    }
