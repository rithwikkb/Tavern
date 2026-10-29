import React, { useState, useEffect } from 'react';
import PageLoader from '../components/PageLoader';
import { useParams, useNavigate } from 'react-router-dom';
import { getAuthorProfile, updateAuthorProfile, uploadProfileImage } from '../services/editProfileService';
import '../styles/pages/EditProfile.css';
import Cookies from 'js-cookie';  

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
                    github: data.github,
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

    // Handle image file upload
    const handleImageUpload = async (e) => {
        const file = e.target.files[0];
        const authorIdFromCookie = Cookies.get('author_id');  // Retrieve author_id from cookies

        if (file && authorIdFromCookie) {
            setImageUploading(true);

            const formDataToUpload = new FormData();
            formDataToUpload.append('profile_image', file);

            try {
                // Upload image to the server
                const response = await uploadProfileImage(authorIdFromCookie, formDataToUpload);  // Upload API call
                if (response.ok) {
                    const result = await response.json();
                    setFormData({
                        ...formData,
                        profileImage: result.url  // Set the image URL returned from the server
                    });
                } else {
                    setErrors({ imageUpload: 'Failed to upload image' });
                }
            } catch (err) {
                console.error('Image upload error:', err);
                setErrors({ imageUpload: 'Image upload failed' });
            } finally {
                setImageUploading(false);
            }
        } else {
            setErrors({ imageUpload: 'Please select a file to upload' });
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

                {/* Profile Image Preview */}
                {formData.profileImage && (
                    <div className="profile-image-preview">
                        <img src={formData.profileImage} alt="Current Profile" />
                    </div>
                )}

                <form onSubmit={handleSubmit} className="edit-profile-form">
                    <div className="form-group">
                        <label htmlFor="displayName">Display Name:</label>
                        <input
                            type="text"
                            authorId="displayName"
                            name="displayName"
                            placeholder="Enter display name"
                            value={formData.displayName}
                            onChange={handleChange}
                        />
                        {errors.displayName && <p className="error">{errors.displayName}</p>}
                    </div>

                    <div className="form-group">
                        <label htmlFor="github">GitHub:</label>
                        <input
                            type="url"
                            authorId="github"
                            name="github"
                            placeholder="Enter GitHub URL"
                            value={formData.github}
                            onChange={handleChange}
                        />
                        {errors.github && <p className="error">{errors.github}</p>}
                    </div>

                    <div className="form-group">
                        <label htmlFor="profileImage">Profile Image:</label>
                        <input
                            type="file"
                            name="profileImage"
                            accept="image/*"
                            onChange={handleImageUpload}  // Handle image file upload
                        />
                        {imageUploading && <p>Uploading image...</p>}
                        {errors.imageUpload && <p className="error">{errors.imageUpload}</p>}
                    </div>

                    {errors.general && <p className="error">{errors.general}</p>}

                    <button type="submit" className="save-button">Save</button>
                </form>
            </div>
        </div>
    );
};

export default EditProfile;
