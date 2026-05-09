import { Pagination } from "react-bootstrap";
import { usePagination } from "../hooks/usePagination";

interface Props {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export default function PaginationControls({
  page,
  totalPages,
  onPageChange,
}: Props) {
  const items = usePagination(page, totalPages);

  if (totalPages <= 1) return null;

  return (
    <div className="d-flex justify-content-center mt-3">
      <Pagination>
        <Pagination.First
          onClick={() => onPageChange(1)}
          disabled={page <= 1}
        />
        <Pagination.Prev
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page <= 1}
        />
        {items.map((item) =>
          typeof item === "number" ? (
            <Pagination.Item
              key={item}
              active={item === page}
              onClick={() => onPageChange(item)}
            >
              {item}
            </Pagination.Item>
          ) : (
            <Pagination.Ellipsis key={item} disabled />
          ),
        )}
        <Pagination.Next
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page >= totalPages}
        />
        <Pagination.Last
          onClick={() => onPageChange(totalPages)}
          disabled={page >= totalPages}
        />
      </Pagination>
    </div>
  );
}
