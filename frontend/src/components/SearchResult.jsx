// https://github.com/CodeCompleteYT/react-search-bar/blob/main/src/components/SearchResult.jsx search result 2024-10-18, author: CodeCompleteYT 

import "../styles/components/SearchResult.css";
import { useNavigate } from "react-router-dom";
import unknownUser from "../assets/unknownUser.png";

const SearchResult = ({ result }) => {
  const navigate = useNavigate();

  const handleClickProfile = async () => {
    const authorId = result.id.replace(/\/$/, '').split('/').slice(-1)[0]; // Grabs the second last segment, which is the UUID
    navigate(`/profile/${authorId}`);
  }

  return (
    <div
      className="search-result"
      onClick={handleClickProfile}
    >
      <img className="search-result-avatar" src={result.profileImage || unknownUser} alt="" loading="lazy" />
      <span>{result.displayName}</span>
    </div>
  );
};

export default SearchResult;