// AI SMART PARKING SYSTEM

let users = JSON.parse(localStorage.getItem("parkingUsers")) || [];
let reservations = JSON.parse(localStorage.getItem("parkingReservations")) || [];
let currentUser = JSON.parse(localStorage.getItem("currentParkingUser")) || null;
let memberships = JSON.parse(localStorage.getItem("parkingMemberships")) || [];

// Vehicle slot capacity
const capacities = {
    Car: 10,
    Bike: 15,
    Cycle: 5
};

// Save data
function saveData() {
    localStorage.setItem("parkingUsers", JSON.stringify(users));
    localStorage.setItem("parkingReservations", JSON.stringify(reservations));
    localStorage.setItem("parkingMemberships", JSON.stringify(memberships));
}

// Page navigation
function showPage(pageId) {
    document.querySelectorAll(".page").forEach(page => {
        page.classList.add("hidden");
    });

    document.getElementById(pageId).classList.remove("hidden");
}

// Registration
document.getElementById("registerForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const name = document.getElementById("regName").value.trim();
    const email = document.getElementById("regEmail").value.trim().toLowerCase();
    const password = document.getElementById("regPassword").value;
    const vehicle = document.getElementById("regVehicle").value;
    const vehicleNumber = document.getElementById("regNumber").value.trim();

    if (users.some(user => user.email === email)) {
        alert("Email already registered!");
        return;
    }

    users.push({
        id: Date.now(),
        name,
        email,
        password,
        vehicle,
        vehicleNumber
    });

    saveData();

    alert("Registration successful! Please login.");
    this.reset();
    showPage("login");
});

// Login
document.getElementById("loginForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const email = document.getElementById("loginEmail").value.trim().toLowerCase();
    const password = document.getElementById("loginPassword").value;

    const user = users.find(
        user => user.email === email && user.password === password
    );

    if (!user) {
        alert("Invalid email or password!");
        return;
    }

    currentUser = user;
    localStorage.setItem("currentParkingUser", JSON.stringify(user));

    this.reset();
    openDashboard();
});

// Dashboard
function openDashboard() {
    if (!currentUser) {
        showPage("login");
        return;
    }

    document.getElementById("welcomeUser").textContent =
        "Welcome, " + currentUser.name + "!";

    showPage("dashboard");
    updateDashboard();
    updateReservations();
    updateMembership();
}

// Get active reservations
function getActiveReservations() {
    return reservations.filter(
        booking =>
            booking.userId === currentUser.id &&
            booking.status !== "Cancelled"
    );
}

// Count available slots
function getVehicleCounts(vehicle) {
    const active = getActiveReservations();

    const occupied = active.filter(
        booking =>
            booking.vehicle === vehicle &&
            booking.status === "Occupied"
    ).length;

    const reserved = active.filter(
        booking =>
            booking.vehicle === vehicle &&
            booking.status === "Reserved"
    ).length;

    return {
        occupied,
        reserved,
        available: capacities[vehicle] - occupied - reserved
    };
}

// Update dashboard
function updateDashboard() {
    const vehicles = ["Car", "Bike", "Cycle"];

    let totalAvailable = 0;
    let totalOccupied = 0;
    let totalReserved = 0;

    vehicles.forEach(vehicle => {
        const counts = getVehicleCounts(vehicle);

        totalAvailable += counts.available;
        totalOccupied += counts.occupied;
        totalReserved += counts.reserved;

        const elementId = vehicle.toLowerCase() + "Available";
        document.getElementById(elementId).textContent = counts.available;
    });

    document.getElementById("totalSlots").textContent = 30;
    document.getElementById("availableSlots").textContent = totalAvailable;
    document.getElementById("occupiedSlots").textContent = totalOccupied;
    document.getElementById("reservedSlots").textContent = totalReserved;
}

// Parking booking
document.getElementById("bookingForm").addEventListener("submit", function(e) {
    e.preventDefault();

    if (!currentUser) {
        alert("Please login first.");
        showPage("login");
        return;
    }

    const location = document.getElementById("bookingLocation").value;
    const vehicle = document.getElementById("bookingVehicle").value;
    const type = document.getElementById("bookingType").value;
    const date = document.getElementById("bookingDate").value;
    const time = document.getElementById("bookingTime").value;

    const counts = getVehicleCounts(vehicle);

    if (counts.available <= 0) {
        alert("Sorry! No available " + vehicle + " slots.");
        return;
    }

    const slotNumber = capacities[vehicle] - counts.available + 1;

    const booking = {
        id: Date.now(),
        userId: currentUser.id,
        location,
        vehicle,
        type,
        date,
        time,
        slot: vehicle + "-" + slotNumber,
        status: type === "Walk-in" ? "Occupied" : "Reserved"
    };

    reservations.push(booking);

    saveData();

    alert(
        "Parking booked successfully!\n" +
        "Booking ID: " + booking.id +
        "\nSlot: " + booking.slot +
        "\nStatus: " + booking.status
    );

    this.reset();
    updateDashboard();
    updateReservations();
});

// Display reservations
function updateReservations() {
    const list = document.getElementById("reservationList");

    const myBookings = reservations.filter(
        booking => booking.userId === currentUser.id
    );

    list.innerHTML = "";

    if (myBookings.length === 0) {
        list.innerHTML =
            '<tr><td colspan="7">No reservations found.</td></tr>';
        return;
    }

    myBookings.forEach(booking => {
        const row = document.createElement("tr");

        const values = [
            booking.id,
            booking.location,
            booking.vehicle,
            booking.type,
            booking.date,
            booking.status
        ];

        values.forEach(value => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
        });

        const actionCell = document.createElement("td");

        if (booking.status !== "Cancelled") {
            const cancelButton = document.createElement("button");
            cancelButton.textContent = "Cancel";
            cancelButton.className = "cancel-btn";
            cancelButton.onclick = () => cancelReservation(booking.id);
            actionCell.appendChild(cancelButton);
        } else {
            actionCell.textContent = "Cancelled";
        }

        row.appendChild(actionCell);
        list.appendChild(row);
    });
}

// Cancel reservation
function cancelReservation(id) {
    const confirmCancel = confirm("Are you sure you want to cancel?");

    if (!confirmCancel) return;

    const booking = reservations.find(
        item => item.id === id && item.userId === currentUser.id
    );

    if (booking) {
        booking.status = "Cancelled";
        saveData();
        updateDashboard();
        updateReservations();
        alert("Reservation cancelled successfully!");
    }
}

// Membership registration
function registerMembership() {
    const existing = memberships.find(
        member => member.userId === currentUser.id
    );

    if (existing) {
        alert("You already have a membership!");
        return;
    }

    const confirmFee = confirm(
        "Demo membership fee is ₹500.\nContinue with demo registration?"
    );

    if (!confirmFee) return;

    memberships.push({
        userId: currentUser.id,
        fee: 500,
        status: "Demo Registered",
        date: new Date().toLocaleDateString()
    });

    saveData();
    updateMembership();

    alert("Demo membership registration successful!");
}

// Membership status
function updateMembership() {
    const member = memberships.find(
        item => item.userId === currentUser.id
    );

    document.getElementById("membershipStatus").textContent =
        member
            ? "Membership: " + member.status
            : "Membership: Not Registered";
}

// Logout
function logout() {
    currentUser = null;
    localStorage.removeItem("currentParkingUser");
    showPage("home");
    alert("Logged out successfully!");
}

// Sample prediction values
function showPredictions() {
    document.getElementById("demandPrediction").textContent = "Medium";
    document.getElementById("occupancyPrediction").textContent = "50%";
    document.getElementById("pricePrediction").textContent = "₹40/hour";
}

// Initial application
showPredictions();

if (currentUser) {
    openDashboard();
} else {
    showPage("home");
}