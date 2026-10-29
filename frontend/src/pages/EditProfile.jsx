import React, { useState, useEffect } from 'react';
import PageLoader from '../components/PageLoader';
import { useParams, useNavigate } from 'react-router-dom';
import { getAuthorProfile, updateAuthorProfile, uploadProfileImage } from '../services/editProfileService';
import '../styles/pages/EditProfile.css';
import Cookies from 'js-cookie';  
import ImagePicker from '../components/ImagePicker';

const EditProfile = () => {
    const { authorId } = useParams();
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        displayName: '',
        github: '',
        profileImage: ''
    });
    const [loading, setLoading] = useState(true);
    const [errors, setErrors] = useState({});
    const [imageUploading, setImageUploading] = useState(false);  // State for image uploading

    // Fetch author details when the component mounts
    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const data = await getAuthorProfile(authorId);
                setFormData({
                    displayName: data.displayName,
                    // new accounts get a bare "https://github.com/" placeholder; show it as empty
                    github: /^https?:\/\/github\.com\/?$/.test(data.github || '') ? '' : data.github,
                    profileImage: data.profileImage
                });
                setLoading(false);
            } catch (error) {
                console.error('Error fetching profile:', error);
            }
        };

        fetchProfile();
    }, [authorId]);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    // Upload the picture as soon as it's chosen; saving the form stores its URL
    const handleImageUpload = async (file) => {
        const authorIdFromCookie = Cookies.get('author_id');  // Retrieve author_id from cookies
        setImageUploading(true);
        setErrors((current) => ({ ...current, imageUpload: undefined }));

        const formDataToUpload = new FormData();
        formDataToUpload.append('profile_image', file);

        try {
            // Upload image to the server
            const response = await uploadProfileImage(authorIdFromCookie, formDataToUpload);  // Upload API call
            const result = await response.json();
            if (response.ok) {
                // functional update so edits made during the upload aren't lost
                setFormData((current) => ({ ...current, profileImage: result.url }));
            } else {
                setErrors((current) => ({ ...current, imageUpload: result.error || result.detail || 'Failed to upload image' }));
            }
        } catch (err) {
            console.error('Image upload error:', err);
            setErrors((current) => ({ ...current, imageUpload: 'Image upload failed' }));
        } finally {
            setImageUploading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Transform formData to match the field names expected by the backend
        const updatedData = {
            display_name: formData.displayName,  // Transform displayName to display_name
            github: formData.github,
            profile_image: formData.profileImage  // Profile image URL from the uploaded image
        };

        try {
            await updateAuthorProfile(authorId, updatedData);  // Send the transformed data
            navigate(`/profile/${authorId}`);
        } catch (error) {
            console.error('Error updating profile:', error);
            setErrors({ general: error.message || 'Failed to update profile' });
        }
    };

    if (loading) {
        return <PageLoader />;
    }

    return (
        <div className="edit-profile-page">
            <div className="edit-profile-container">
                <h1>Edit Profile</h1>

                <form onSubmit={handleSubmit} className="edit-profile-form">
                    <div className="form-group">
                        <span className="field-label">Profile picture</span>
                        <ImagePicker
                            imageUrl={formData.profileImage}
                            uploading={imageUploading}
                            error={errors.imageUpload}
                            onFileSelected={handleImageUpload}
                        />
                    </div>

                    <div className="form-group">
                        <label className="field-label" htmlFor="edit-display-name">Display name</label>
                        <input
                            type="text"
                            id="edit-display-name"
                            name="displayName"
                            placeholder="Your name"
                            value={formData.displayName}
                            onChange={handleChange}
                            required
                        />
                        {errors.displayName && <p className="error">{errors.displayName}</p>}
                    </div>

                    <div className="form-group">
                        <label className="field-label" htmlFor="edit-github">
                            GitHub link <span className="optional-tag">optional</span>
                        </label>
                        <input
                            type="url"
                            id="edit-github"
                            name="github"
                            placeholder="https://github.com/you"
                            value={formData.github}
                            onChange={handleChange}
                        />
                        {errors.github && <p className="error">{errors.github}</p>}
                    </div>

                    {errors.general && <p className="error" role="alert">{errors.general}</p>}

                    <div className="edit-profile-actions">
                        <button type="button" className="cancel-button" onClick={() => navigate(`/profile/${authorId}`)}>
                            Cancel
                        </button>
                        <button type="submit" className="save-button" disabled={imageUploading}>
                            Save
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default EditProfile;
