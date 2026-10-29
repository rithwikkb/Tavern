// https://mui.com/material-ui/react-modal/ for 'Basic Modal' code from MUI to show comments, 2024-10-31
// https://mui.com/material-ui/react-list/ for List of Avatars, sections 'Align list items' and 'Selected ListItem', 2024-10-31
import React from 'react';
import Modal from '@mui/material/Modal';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Avatar from '@mui/material/Avatar';
import List from '@mui/material/List';
import ListItemAvatar from '@mui/material/ListItemAvatar';
import ListItemText from '@mui/material/ListItemText';
import ListItemButton from '@mui/material/ListItemButton';
import { useNavigate } from 'react-router-dom';
import '../styles/components/AuthorsListModal.css'

const AuthorsListModal = ({ authors, onModalClose, title = "Authors" }) => { /* authors is the list of Author objects that should be displayed in modal*/
const navigate = useNavigate();

const handleClickProfile = async (author) => {
    const authorId = author.id.replace(/\/$/, '').split('/').slice(-1)[0];
    navigate(`/profile/${authorId}`);
  }


return (
    <Modal 
        open={true} 
        onClose={onModalClose} 
        aria-labelledby="authors-list-title"
    >
        <Box className={'modalBox authors-modal'}>
            <Typography id="authors-modal-title" variant="h6" component="h2">
                {title}
            </Typography>
            {authors.length === 0 && (
                <Typography className="authors-list-empty">No one here yet.</Typography>
            )}
            <List className={'authors-list-container'}>
            {authors.map((author) => (
                <ListItemButton key={author.id} className={'authors-list-item'} onClick={() => handleClickProfile(author)}>
                <ListItemAvatar>
                    <Avatar src={author.profileImage} alt={author.displayName}>
                    {author.displayName[0]} {/* Fallback for initials */}
                    </Avatar>
                </ListItemAvatar>
                <ListItemText
                    primary={author.displayName}
                />
                </ListItemButton>
            ))}
            </List>
        </Box>
    </Modal>
)
};

export default AuthorsListModal;